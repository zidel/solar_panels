import argparse
import pathlib
import sys

import tensorflow

import database
import model
import score_tiles
import util


def load_image_from_path(input_path, channels):
    input_data = tensorflow.io.read_file(input_path)
    input_data = tensorflow.io.decode_jpeg(input_data, channels=channels)
    input_data = tensorflow.cast(input_data, tensorflow.float32)# / 255.0
    input_data = tensorflow.keras.applications.vgg19.preprocess_input(input_data)
    return input_data


def load_nib_data(path):
    return load_image_from_path(path, 3)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--model', default='VGG19')
    parser.add_argument('--load-model', default='data/model.hdf5')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--tile-path', type=str, default="data/images")
    parser.add_argument('--batch-size', default=10, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)
    model_version = util.hash_file(args.load_model)
    nib_api_key = util.load_key(args.NiB_key)
    image_dir = pathlib.Path(args.tile_path)

    with db.transaction() as c:
        c.execute('''select tile_hash, score
                     from with_solar
                     natural left join scores
                     where model_version is null or model_version != ?
                  ''',
                  (model_version,))
        tiles = c.fetchall()

    progress = score_tiles.Progress()
    progress.remaining(len(tiles))
    try:
        score_tiles.score_tiles(
                db,
                image_dir,
                nib_api_key,
                progress,
                model.get(args.model, args.load_model),
                model_version,
                args.batch_size,
                None,
                tiles)
    finally:
        progress.clear()

    with db.transaction() as c:
        c.execute('''select has_solar, score
                     from with_solar
                     natural join scores
                     where model_version = ?
                  ''',
                  [model_version])
        data = c.fetchall()

    labels = []
    predictions = []
    for has_solar, result in data:
        labels.append(2 if has_solar else 0)

        if result < 0.1:
            predictions.append(0)
        elif result < 0.9:
            predictions.append(1)
        else:
            predictions.append(2)

    print()
    matrix = tensorflow.math.confusion_matrix(labels, predictions)
    print(matrix)
    return 0


if __name__ == '__main__':
    sys.exit(main())
