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


def print_matrix(matrix):
    total = int(sum(sum(matrix)))
    results = {
            'false': {
                'negative': int(matrix[0][0]),
                'unknown': int(matrix[0][1]),
                'positive': int(matrix[0][2]),
                },
            'unknown': {
                'negative': int(matrix[1][0]),
                'unknown': int(matrix[1][1]),
                'positive': int(matrix[1][2]),
                },
            'true': {
                'negative': int(matrix[2][0]),
                'unknown': int(matrix[2][1]),
                'positive': int(matrix[2][2]),
                },
            }

    print('      P_neg  P_unk  P_pos')
    print('Pos: {: 6d} {: 6d} {: 6d}'.format(
        results['true']['negative'],
        results['true']['unknown'],
        results['true']['positive']))
    print('Unk: {: 6d} {: 6d} {: 6d}'.format(
        results['unknown']['negative'],
        results['unknown']['unknown'],
        results['unknown']['positive']))
    print('Neg: {: 6d} {: 6d} {: 6d}'.format(
        results['false']['negative'],
        results['false']['unknown'],
        results['false']['positive']))

    true_positives = int(matrix[2][2])
    all_pred_positive = int(matrix[0][2] + matrix[1][2] + matrix[2][2])
    all_real_positive = int(sum(matrix[2]))

    precision = true_positives / all_pred_positive
    recall = true_positives / all_real_positive
    f_score = (2 * precision * recall) / (precision + recall)

    print()
    print('Positive accuracy: {:.0f}%'.format(
        100 * precision))
    print('Positive coverage: {:.0f}%'.format(
        100 * recall))
    print('          F-score: {:.0f}%'.format(
        100 * f_score))


def print_num_positive_in_top(tiles):
    tiles.sort(key=lambda t: t[2], reverse=True)
    tiles = tiles[:1000]

    try:
        num_solar = sum([t[1] for t in tiles])
        print(f'  Solar in top 1k: {num_solar}')
    except TypeError:
        num_missing = sum([1 if t[1] is None else 0 for t in tiles])
        print(f'Review {num_missing} more tiles to get 1k count')


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
        tiles_for_scoring = database.validation_tiles_for_scoring(
                c, model_version)

    progress = score_tiles.Progress()
    progress.remaining(len(tiles_for_scoring))
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
                tiles_for_scoring)
    finally:
        progress.clear()

    with db.transaction() as c:
        tiles = database.validation_tiles(c)

    labels = []
    predictions = []
    for _, has_solar, score in tiles:
        if has_solar is None:
            labels.append(1)
        elif has_solar:
            labels.append(2)
        else:
            labels.append(0)

        if score < 0.1:
            predictions.append(0)
        elif score < 0.9:
            predictions.append(1)
        else:
            predictions.append(2)

    matrix = tensorflow.math.confusion_matrix(labels, predictions)
    print_matrix(matrix)
    print_num_positive_in_top(tiles)

    return 0


if __name__ == '__main__':
    sys.exit(main())
