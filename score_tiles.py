import argparse
import datetime
import pathlib
import sys
import time

import sqlite3
import tensorflow

import database
import model
import util


class Progress(object):
    def __init__(self):
        self._start_time = time.time()
        self._total = 0
        self.done = 0
        self._score_dist = dict(((x, 0) for x in range(10)))

    def remaining(self, count):
        self._total = max(count + self.done, self._total)

    def finished(self, count, score, prev_score):
        self.done += count
        score_bin = max(min(int(score * 10), 9), 0)
        self._score_dist[score_bin] += 1

        if self.done >= self._total:
            self.clear()
            return

        since_start = time.time() - self._start_time
        rate = self.done / since_start
        seconds_left = int((self._total - self.done) / rate)
        eta = datetime.timedelta(seconds=seconds_left)

        score_dist = '/'.join([
            '{}'.format(self._score_dist[i])
            for i
            in self._score_dist])

        if prev_score is not None:
            prev_score_str = '{:.2f}'.format(prev_score)
        else:
            prev_score_str = 'N/A'

        fmt = '\r{}/{} done, {:.2f} steps/s, {} remaining, {} -> {:.2f}, {}{}'
        sys.stderr.write(fmt.format(
            self.done,
            self._total,
            rate,
            eta,
            prev_score_str,
            score,
            score_dist,
            ' ' * 10))

    def log(self, msg, *args):
        self.clear()
        print(msg.format(*args))

    def clear(self):
        sys.stderr.write(' ' * 60)
        sys.stderr.write('\r')
        sys.stderr.flush()


def load_image_from_path(input_path, channels):
    input_data = tensorflow.io.read_file(input_path)
    input_data = tensorflow.io.decode_jpeg(input_data, channels=channels)
    input_data = tensorflow.cast(input_data, tensorflow.float32)  # / 255.0
    return input_data


def load_nib_data(path):
    return load_image_from_path(path, 3)


def score_tiles(db, image_dir, nib_api_key, feature_name, progress, m,
                model_version, batch_size, limit, tiles):
    if not tiles:
        return

    paths = []
    for tile_data in tiles:
        tile_hash = tile_data[0]
        dir_name = tile_hash[:2]
        file_name = tile_hash[2:]
        path = image_dir / f'{dir_name}/{file_name}.jpeg'
        paths.append(str(path))

    dataset = tensorflow.data.Dataset.from_tensor_slices(paths)
    dataset = dataset.map(
            load_nib_data,
            num_parallel_calls=tensorflow.data.AUTOTUNE)
    dataset = dataset.batch(batch_size)

    now = datetime.datetime.now()
    timestamp = now.isoformat()

    image_index = 0
    for batch in dataset:
        results = m.predict(batch, batch_size=batch_size)
        while True:
            try:
                with db.transaction() as c:
                    for result in results:
                        tile_data = tiles[image_index]
                        database.write_score(
                                c,
                                tile_data[0],
                                feature_name,
                                float(result),
                                model_version,
                                timestamp)
                        image_index += 1
                        progress.finished(1, float(result), tile_data[1])
                break
            except sqlite3.OperationalError as e:
                print(e)
                continue

        if limit and image_index >= limit:
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--tile-path', type=str, default="data/images")
    parser.add_argument('--model', default='VGG19')
    parser.add_argument('--load-model', default='data/model.hdf5')
    parser.add_argument('--limit', type=int)
    parser.add_argument('--feature', type=str, default='solar')

    parser.add_argument('--batch-size', default=10, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)
    model_version = util.hash_file(args.load_model)
    nib_api_key = util.load_key(args.NiB_key)
    image_dir = pathlib.Path(args.tile_path)

    m = model.get(args.model, args.load_model)

    progress = Progress()
    try:
        while True:
            tiles, count = db.tiles_for_scoring(model_version, args.feature,
                                                1000000)
            if not tiles:
                break

            progress.remaining(count)
            score_tiles(db, image_dir, nib_api_key, args.feature, progress, m,
                        model_version, args.batch_size, args.limit, tiles)
    finally:
        progress.clear()
        print('Scored {} tiles'.format(progress.done))


if __name__ == '__main__':
    main()
