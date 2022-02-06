import argparse
import datetime
import math
import pathlib
import random

import tensorflow as tf

import database
import model


def tile_to_paths(z, x, y):
    return pathlib.Path('data/NiB/{}/{}/{}.jpeg'.format(z, x, y))


def read_image(path, channels=3):
    data = tf.io.read_file(path)
    data = tf.io.decode_jpeg(data, channels=channels)
    return tf.cast(data, tf.float32) / 255.0


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


def apply_rotation(tiles):
    output = []
    for tile in tiles:
        for rotations in range(4):
            copy = list(tile)
            copy[2] = str(rotations)
            output.append(tuple(copy))

    return output


def apply_horizontal_flips(tiles):
    output = []
    for tile in tiles:
        for left_right in [0, 1]:
            copy = list(tile)
            copy[3] = str(left_right)
            output.append(tuple(copy))

    return output


def apply_vertical_flips(tiles):
    output = []
    for tile in tiles:
        for up_down in [0, 1]:
            copy = list(tile)
            copy[4] = str(up_down)
            output.append(tuple(copy))

    return output


def augment_tiles(solar, non_solar):
    solar = apply_rotation(solar)
    solar = apply_horizontal_flips(solar)
    solar = apply_vertical_flips(solar)

    non_solar_scaling_needed = len(solar) / len(non_solar)
    print('Want to scale background by {:.3f}'.format(
        non_solar_scaling_needed))

    if non_solar_scaling_needed > 2:
        print('Applying rotations to background tiles')
        non_solar = apply_rotation(non_solar)
        non_solar_scaling_needed /= 4

    if non_solar_scaling_needed > 1:
        print('Applying horizontal flips to background tiles')
        non_solar = apply_horizontal_flips(non_solar)
        non_solar_scaling_needed /= 2

    if non_solar_scaling_needed > 1:
        print('Applying vertical flips to background tiles')
        non_solar = apply_vertical_flips(non_solar)
        non_solar_scaling_needed /= 2

    return solar, non_solar


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--load-model', type=str)
    parser.add_argument('--save-to', type=str, default='data/model.hdf5')

    parser.add_argument('--batch-size', default=128, type=int)
    parser.add_argument('--step-count', default=500000, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)
    tiles_with_solar = []
    tiles_without_solar = []
    for z, x, y, has_solar in db.trainable():
        nib_path = tile_to_paths(z, x, y)
        data = (str(nib_path),
            'true' if has_solar else 'false',
            '0',
            '0',
            '0',
            )
        if has_solar:
            tiles_with_solar.append(data)
        else:
            tiles_without_solar.append(data)

    print('Before augmentation: {} solar / {} non solar'.format(
        len(tiles_with_solar),
        len(tiles_without_solar),
        ))
    tiles_with_solar, tiles_without_solar = augment_tiles(
            tiles_with_solar,
            tiles_without_solar)
    print('After augmentation: {} solar / {} non solar'.format(
        len(tiles_with_solar),
        len(tiles_without_solar),
        ))
    random.shuffle(tiles_with_solar)
    random.shuffle(tiles_without_solar)

    images_per_category = min(len(tiles_with_solar), len(tiles_without_solar))
    tiles = tiles_with_solar[:images_per_category] \
        + tiles_without_solar[:images_per_category]
    training_set_size = int(len(tiles) * 0.9)

    random.shuffle(tiles)
    training_tiles = tiles[:training_set_size]
    validation_tiles = tiles[training_set_size:]
    print('Training with {} tiles, validating with {}'.format(
        len(training_tiles),
        len(validation_tiles),
        ))

    input_images = training_set_size
    batch_count = math.ceil(input_images / args.batch_size)
    epochs = math.ceil(args.step_count / input_images)
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

    validation_data = tf.data.Dataset.from_tensor_slices(validation_tiles)
    validation_data = validation_data.map(load_image_data,
                                          num_parallel_calls=tf.data.AUTOTUNE)
    validation_data = validation_data.batch(args.batch_size)

    m = model.classify(args.load_model)

    callbacks = [
            tf.keras.callbacks.TensorBoard(
                log_dir='data/tensorboard/{}'.format(datetime.datetime.now()),
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
