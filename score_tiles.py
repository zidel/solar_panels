import argparse
import datetime
import hashlib
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
        self.done = 0

    def finished(self, count):
        self.done += count

        if self.done >= self._total:
            self.clear()
            return

        since_start = time.time() - self._start_time
        rate = self.done / since_start
        seconds_left = (self._total - self.done) / rate
        eta = datetime.timedelta(seconds=seconds_left)

        sys.stderr.write('\r{}/{} done, {:.2f} steps/s, {} remaining{}'.format(
            self.done,
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


def process_prediction(cursor, tile, result, model_version):
    now = datetime.datetime.now()
    timestamp = now.isoformat()

    database.write_score(
            cursor,
            tile[0],
            tile[1],
            tile[2],
            float(result),
            model_version,
            timestamp)


def hash_model(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            data = f.read(1024 * 1024)
            if len(data) == 0:
                break

            h.update(data)

    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--model', default='data/model.hdf5')
    parser.add_argument('--limit', type=int)

    parser.add_argument('--batch-size', default=2, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)
    model_version = hash_model(args.model)

    tiles = list(db.tiles_for_scoring(model_version))
    filtered_tiles = []
    paths = []
    for tile in tiles:
        path = tile_to_path(tile, 'NiB')
        if pathlib.Path(path).exists():
            paths.append(path)
            filtered_tiles.append(tile)

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
                    process_prediction(
                            c,
                            filtered_tiles[image_index],
                            result,
                            model_version)
                    image_index += 1

            progress.finished(len(results))
            if args.limit and image_index >= args.limit:
                break
    finally:
        progress.clear()
        print('Scored {} tiles'.format(progress.done))


if __name__ == '__main__':
    main()
