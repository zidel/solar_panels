import argparse
import datetime
import math
import pathlib

import tensorflow as tf

import database
import feature
import model
import util


def read_image(path, channels=3):
    data = tf.io.read_file(path)
    data = tf.io.decode_jpeg(data, channels=channels)
    return tf.cast(data, tf.float32)  # / 255.0


def load_image_data(tile_data):
    nib_path = tile_data[0]
    correct = 1.0 if tile_data[1] == 'true' else 0.0
    rotations = int(tile_data[2])
    left_right_flip = int(tile_data[3])
    up_down_flip = int(tile_data[4])

    nib_data = read_image(nib_path, channels=3)
    nib_data = tf.image.rot90(nib_data, k=rotations)
    if left_right_flip == 1:
        nib_data = tf.image.flip_left_right(nib_data)
    if up_down_flip == 1:
        nib_data = tf.image.flip_left_right(nib_data)

    return (nib_data, correct)


def apply_rotation(tiles, add_up_to=-1):
    output = list(tiles)
    for tile in tiles:
        for rotations in range(1, 4):
            if add_up_to == 0:
                return output

            copy = list(tile)
            copy[2] = str(rotations)
            output.append(tuple(copy))

            add_up_to -= 1

    return output


def apply_horizontal_flips(tiles, add_up_to=-1):
    output = list(tiles)
    for tile in tiles:
        if add_up_to == 0:
            break

        copy = list(tile)
        copy[3] = '1'
        output.append(tuple(copy))

        add_up_to -= 1

    return output


def apply_vertical_flips(tiles, add_up_to=-1):
    output = list(tiles)
    for tile in tiles:
        if add_up_to == 0:
            break

        copy = list(tile)
        copy[4] = '1'
        output.append(tuple(copy))

        add_up_to -= 1

    return output


def augment_tiles(tiles, background_scale):
    solar = []
    non_solar = []
    for data in tiles:
        if data[1] == 'true':
            solar.append(data)
        else:
            non_solar.append(data)

    solar = apply_rotation(solar)
    solar = apply_horizontal_flips(solar)
    solar = apply_vertical_flips(solar)

    print(f'Initially: {len(solar)}S, {len(non_solar)}BG')
    target_count = int(background_scale * len(solar))
    print('Want to scale background to {}, {:.3f}'.format(
        target_count,
        target_count / len(non_solar)))

    non_solar = apply_horizontal_flips(non_solar,
                                       target_count - len(non_solar))
    non_solar = apply_rotation(non_solar, target_count - len(non_solar))
    non_solar = apply_vertical_flips(non_solar, target_count - len(non_solar))

    bg_ratio = len(non_solar) / len(solar)
    print(f'Result: {len(solar)}S, {len(non_solar)}BG, {bg_ratio}')

    return solar + non_solar


def format_tile_data(image_dir, tiles):
    result = []
    for tile_hash, has_solar, _ in tiles:
        if has_solar is None:
            continue

        nib_path = util.tile_to_paths(image_dir, tile_hash)
        result.append((str(nib_path),
                       'true' if has_solar else 'false',
                       '0',  # Rotate
                       '0',  # Horizontal flip
                       '0',  # Vertical flip
                       ))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--tile-path', type=str, default='data/images')
    parser.add_argument('--model', type=str, default='VGG19')
    parser.add_argument('--load-model', type=str)
    parser.add_argument('--save-to', type=str, default='data/model.hdf5')
    parser.add_argument('--tensorboard', type=str, default=None)
    parser.add_argument('--feature', type=str, required=True)

    parser.add_argument('--batch-size', default=256, type=int)
    parser.add_argument('--step-count', default=500000, type=int)
    parser.add_argument('--learning-rate', default=1e-4, type=float)
    parser.add_argument('--background-scale', default=1.0, type=float)
    args = parser.parse_args()

    image_dir = pathlib.Path(args.tile_path)

    db = database.Database(args.database)
    with db.transaction('get_tiles_for_training') as c:
        training_tiles = format_tile_data(
                image_dir,
                database.training_tiles(c, args.feature))
        validation_tiles = format_tile_data(
                image_dir,
                database.validation_tiles(c, args.feature))

    training_tiles = augment_tiles(training_tiles, args.background_scale)
    print('Training with {} tiles, validating with {}'.format(
        len(training_tiles),
        len(validation_tiles),
        ))

    input_images = len(training_tiles)
    batch_count = math.ceil(input_images / args.batch_size)
    epochs = math.ceil(args.step_count / input_images)
    epochs = min(epochs, 10)
    print('{} images / batch * {} batches * {} epochs -> {} steps'.format(
        args.batch_size,
        batch_count,
        epochs,
        args.batch_size * batch_count * epochs))

    dataset = tf.data.Dataset.from_tensor_slices(training_tiles)
    dataset = dataset.shuffle(input_images)
    dataset = dataset.map(load_image_data, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.batch(args.batch_size)
    dataset = dataset.repeat()

    validation_data = None
    if validation_tiles:
        validation_data = tf.data.Dataset.from_tensor_slices(validation_tiles)
        validation_data = validation_data.map(
                load_image_data,
                num_parallel_calls=tf.data.AUTOTUNE)
        validation_data = validation_data.batch(args.batch_size)

    m = model.get(args.model,
                  feature.result_type(args.feature),
                  args.load_model,
                  args.learning_rate)

    if args.tensorboard is None:
        tensorboard_name = '{}'.format(datetime.datetime.now())
    else:
        tensorboard_name = args.tensorboard

    callbacks = [
            tf.keras.callbacks.TensorBoard(
                log_dir='data/tensorboard/{}'.format(tensorboard_name),
                histogram_freq=1,
                write_steps_per_second=True,
                update_freq='batch'),
            tf.keras.callbacks.ModelCheckpoint(
                filepath='data/model.hdf5',
                monitor='val_precision'),
            ]

    m.fit(dataset,
          batch_size=args.batch_size,
          callbacks=callbacks,
          epochs=epochs,
          steps_per_epoch=batch_count,
          validation_data=validation_data,
          )
    m.save(args.save_to, save_format='h5')


if __name__ == '__main__':
    main()
