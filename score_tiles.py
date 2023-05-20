import argparse
import datetime
import pathlib
import sys
import tensorflow
import time

import download_tiles
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

        prev_score_str = '{:.2f}'.format(prev_score) if prev_score else 'N/A'
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


def score_tiles(db, nib_api_key, progress, m, model_version, batch_size, limit,
                tiles):
    if not tiles:
        return

    paths = []
    for tile in tiles:
        z = tile[0]
        x = tile[1]
        y = tile[2]
        path = '/mnt/NiB/{}/{}/{}.jpeg'.format(z, x, y)
        paths.append(path)
        if not pathlib.Path(path).exists():
            progress.log('Downloading {}/{}/{}'.format(z, x, y))
            download_tiles.download_single_tile(nib_api_key, z, x, y)

    dataset = tensorflow.data.Dataset.from_tensor_slices(paths)
    dataset = dataset.map(
            load_nib_data,
            num_parallel_calls=tensorflow.data.AUTOTUNE)
    dataset = dataset.batch(batch_size)

    image_index = 0
    for batch in dataset:
        results = m.predict(batch, batch_size=batch_size)
        with db.transaction() as c:
            for result in results:
                tile = tiles[image_index]
                process_prediction(
                        c,
                        tile,
                        result,
                        model_version)
                image_index += 1
                progress.finished(1, float(result), tile[3])

        if limit and image_index >= limit:
            break


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--NiB-key', type=str, default="secret/NiB_key.json")
    parser.add_argument('--model', default='VGG19')
    parser.add_argument('--load-model', default='data/model.hdf5')
    parser.add_argument('--limit', type=int)

    parser.add_argument('--batch-size', default=10, type=int)
    args = parser.parse_args()

    db = database.Database(args.database)
    model_version = util.hash_file(args.load_model)
    nib_api_key = util.load_key(args.NiB_key)

    m = model.get(args.model, args.load_model)

    progress = Progress()
    try:
        while True:
            tiles, count = db.tiles_for_scoring(model_version, 1000)
            if not tiles:
                break

            progress.remaining(count)
            score_tiles(db, nib_api_key, progress, m, model_version,
                        args.batch_size, args.limit, tiles)
    finally:
        progress.clear()
        print('Scored {} tiles'.format(progress.done))


if __name__ == '__main__':
    main()
