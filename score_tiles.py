import argparse
import datetime
import pathlib
import sys
import tensorflow
import time

import database
import model


class Progress(object):
    def __init__(self, total):
        self._start_time = time.time()
        self._total = total
        self._done = 0

    def finished(self, count):
        self._done += count

        if self._done >= self._total:
            self.clear()
            return

        since_start = time.time() - self._start_time
        rate = self._done / since_start
        seconds_left = (self._total - self._done) / rate
        eta = datetime.timedelta(seconds=seconds_left)

        sys.stderr.write('\r{}/{} done, {:.2f} steps/s, {} remaining{}'.format(
            self._done,
            self._total,
            rate,
            eta,
            ' ' * 10))

    def clear(self):
        sys.stderr.write(' ' * 60)
        sys.stderr.write('\r')
        sys.stderr.flush()


def tile_to_path(tile, dataset):
    z = tile[0]
    x = tile[1]
    y = tile[2]
    return 'data/{}/{}/{}/{}.jpeg'.format(dataset, z, x, y)


def load_image_from_path(input_path, channels):
    input_data = tensorflow.io.read_file(input_path)
    input_data = tensorflow.io.decode_jpeg(input_data, channels=channels)
    input_data = tensorflow.cast(input_data, tensorflow.float32) / 255.0
    return input_data


def load_nib_data(path):
    return load_image_from_path(path, 3)


def process_prediction(cursor, tile, result):
    database.write_score(cursor, tile[0], tile[1], tile[2], float(result))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--model', default='data/model.hdf5')
    parser.add_argument('--limit', type=int)

    parser.add_argument('--batch-size', default=2, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)

    tiles = list(db.tiles())
    paths = []
    for tile in tiles:
        # Limit to greater Oslo area to reduce runtime for now
        x = tile[1]
        if x < 138390 or x > 139284:
            continue

        y = tile[2]
        if y < 75810 or y > 76610:
            continue

        path = tile_to_path(tile, 'NiB')
        if pathlib.Path(path).exists():
            paths.append(path)

    skipped = len(tiles) - len(paths)
    if skipped:
        print('Skipping {} tiles without image data'.format(skipped))

    dataset = tensorflow.data.Dataset.from_tensor_slices(paths)
    dataset = dataset.map(
            load_nib_data,
            num_parallel_calls=tensorflow.data.AUTOTUNE)
    dataset = dataset.batch(args.batch_size)

    m = model.classify(args.model)

    progress = Progress(len(paths))
    try:
        image_index = 0
        for batch in dataset:
            results = m.predict(batch, batch_size=args.batch_size)
            with db.transaction() as c:
                for result in results:
                    process_prediction(c, tiles[image_index], result)
                    image_index += 1

            progress.finished(len(results))
            if args.limit and image_index >= args.limit:
                break
    finally:
        progress.clear()


if __name__ == '__main__':
    main()
