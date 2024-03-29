import datetime
import logging
import sqlite3

import feature


log = logging.getLogger('database')


def temporary_error(sqlite_exception):
    temporary_errors = [
            (sqlite3.OperationalError, 'SQLITE_BUSY'),
            ]
    error = (type(sqlite_exception), sqlite_exception.sqlite_errorname)
    return error in temporary_errors


class Database(object):
    def __init__(self, path):
        self._db = sqlite3.Connection(path)

        while True:
            try:
                self._init_database()
                break
            except sqlite3.OperationalError:
                continue

    def _cursor(self):
        c = self._db.cursor()
        c.execute('pragma foreign_keys = true')
        return c

    def transaction(self, name):
        class Transaction(object):
            def __init__(self, cursor, name):
                self._cursor = cursor
                self._name = name

            def __enter__(self):
                self._cursor.execute('begin')
                return self._cursor

            def __exit__(self, type, value, traceback):
                if type is None and value is None and traceback is None:
                    try:
                        self._cursor.execute('commit')
                    except sqlite3.OperationalError:
                        self._cursor.execute('rollback')
                        raise
                else:
                    self._cursor.execute('rollback')

        return Transaction(self._cursor(), name)

    def _init_database(self):
        with self.transaction('create_tables') as c:
            c.execute('''create table if not exists last_update (
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             timestamp string not null,
                             primary key (z, x, y))
                      ''')
            c.execute('''create table if not exists tile_positions (
                             tile_hash string not null,
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             added string not null,
                             primary key (tile_hash),
                             foreign key (z, x, y) references last_update)
                      ''')
            c.execute('''create table if not exists has_feature (
                             tile_hash string not null,
                             feature_name string not null,
                             has_feature bool not null,
                             primary key (tile_hash, feature_name),
                             foreign key (tile_hash) references tile_positions)
                      ''')
            c.execute('''create table if not exists true_score (
                             tile_hash string not null,
                             feature_name string not null,
                             score real not null,
                             primary key (tile_hash, feature_name),
                             foreign key (tile_hash) references tile_positions)
                      ''')
            c.execute('''create table if not exists scores (
                             tile_hash string not null,
                             feature_name string not null,
                             score real not null,
                             model_version string not null,
                             timestamp string not null,
                             primary key (tile_hash, feature_name),
                             foreign key (tile_hash) references tile_positions)
                      ''')
            c.execute('''create table if not exists training_set (
                             feature_name string not null,
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             primary key (feature_name, z, x, y),
                             foreign key (z, x, y) references last_update)
                      ''')
            c.execute('''create table if not exists validation_set (
                             feature_name string not null,
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             primary key (feature_name, z, x, y),
                             foreign key (z, x, y) references last_update)
                      ''')

    def tiles_for_scoring(self, current_model, feature_name, limit):
        query_fmt = '''select {}
                       from tile_positions
                       natural left join (
                           select tile_hash, score, model_version
                           from scores
                           where feature_name = ?
                           )
                       where
                           model_version is null
                           or model_version != ?
                       {}
                    '''
        with self.transaction('get_tiles_for_scoring') as c:
            c.execute(query_fmt.format('count(*)', ''),
                      [feature_name, current_model])
            count = c.fetchone()[0]

            c.execute(query_fmt.format('tile_hash, score',
                                       'order by score desc limit ?'),
                      [feature_name, current_model, limit])
            tiles = c.fetchall()

        return (tiles, count)

    def tiles_for_review(self, feature_name, limit):
        if feature_name == 'solar_area':
            return self.tiles_for_review_area(feature_name, limit)
        else:
            return self.tiles_for_review_normal(feature_name, limit)

    def tiles_for_review_normal(self, feature_name, limit):
        review_most_likely = True

        ordering = 'abs(score - 0.5) asc'
        if review_most_likely:
            ordering = 'score desc'

        with self.transaction('get_tiles_for_review_normal') as c:
            model_query = '''select model_version
                             from scores
                             where
                                 feature_name = ?
                                 and timestamp in (
                                     select max(timestamp)
                                     from scores
                                     natural left join (
                                         select 1 as t, tile_hash
                                         from has_feature
                                         where feature_name = ?)
                                     where
                                         t is null
                                         and feature_name = ?
                                 )
                             limit 1
                          '''

            c.execute(model_query, [feature_name, feature_name, feature_name])
            model_version = c.fetchone()
            if model_version is None:
                return []

            query_fmt = '''select tile_hash, z, x, y, score, model_version
                           from scores
                           natural left join (
                              select 1 as t, tile_hash
                              from has_feature
                              where feature_name = ?)
                           natural join tile_positions
                           where t is null
                                 and feature_name = ?
                                 and score is not null
                                 and model_version = ?
                           order by {}
                           limit ?
                        '''
            query = query_fmt.format(
                    ordering,
                    )
            c.execute(query, [feature_name,
                              feature_name,
                              model_version[0],
                              limit])
            return c.fetchall()

    def tiles_for_review_area(self, feature_name, limit):
        with self.transaction('get_tiles_for_review_area') as c:
            model_query = '''select model_version
                             from scores
                             where
                                 feature_name = ?
                                 and timestamp in (
                                     select max(timestamp)
                                     from scores
                                     natural left join (
                                         select 1 as t, tile_hash
                                         from true_score
                                         where feature_name = ?)
                                     where
                                         t is null
                                         and feature_name = ?
                                 )
                             limit 1
                          '''

            c.execute(model_query, [feature_name, feature_name, feature_name])
            model_version = c.fetchone()
            if model_version is None:
                return []

            query_fmt = '''select scores.tile_hash,
                                  z,
                                  x,
                                  y,
                                  score,
                                  model_version
                           from scores
                           left join (
                              select 1 as t, tile_hash
                              from true_score
                              where feature_name = ?) as ground_truth
                           on ground_truth.tile_hash = scores.tile_hash
                           natural join tile_positions
                           where t is null
                                 and feature_name = ?
                                 and score is not null
                                 and model_version = ?
                           order by score desc
                           limit ?
                        '''
            query = query_fmt
            c.execute(query, [feature_name,
                              feature_name,
                              model_version[0],
                              limit])
            return c.fetchall()

    def tiles_with_solar(self):
        with self.transaction('get_tiles_with_solar') as c:
            c.execute('''select tile_hash
                         from with_solar
                         where has_solar = True
                      ''')
            return c.fetchall()


def get_tile_hash(cursor, z, x, y):
    assert type(z) == int
    assert type(x) == int
    assert type(y) == int

    cursor.execute('''select tile_hash
                      from tile_positions
                      where z = ?
                            and x = ?
                            and y = ?
                   ''',
                   (z, x, y))
    return [tile_hash for tile_hash, in cursor]


def get_tile_pos(cursor, tile_hash):
    assert type(tile_hash) == str

    cursor.execute('''select z, x, y
                      from tile_positions
                      where tile_hash = ?
                   ''',
                   [tile_hash])
    return cursor.fetchone()


def add_tile(cursor, z, x, y):
    assert type(z) == int
    assert type(x) == int
    assert type(y) == int

    epoch = datetime.datetime.fromtimestamp(0)
    timestamp = epoch.isoformat()
    cursor.execute('''insert into last_update
                      (z, x, y, timestamp)
                      values (?, ?, ?, ?)
                      on conflict do nothing
                   ''',
                   (z, x, y, timestamp))


def has_tile(cursor, z, x, y):
    assert type(z) == int
    assert type(x) == int
    assert type(y) == int

    cursor.execute('''select count(*)
                      from tile_positions
                      where z = ?
                            and x = ?
                            and y = ?
                   ''',
                   (z, x, y))
    return cursor.fetchone()[0] > 0


def add_tile_hash(cursor, z, x, y, tile_hash):
    assert type(z) == int
    assert type(x) == int
    assert type(y) == int
    assert type(tile_hash) == str

    add_tile(cursor, z, x, y)

    now = datetime.datetime.now()
    timestamp = now.isoformat()
    cursor.execute('''insert into tile_positions
                      (tile_hash, z, x, y, added)
                      values (?, ?, ?, ?, ?)
                      on conflict do nothing
                   ''',
                   (tile_hash, z, x, y, timestamp))


def get_score(cursor, tile_hash, feature_name):
    cursor.execute('''select score
                      from scores
                      where
                          tile_hash = ?
                          and feature_name = ?
                   ''',
                   [tile_hash, feature_name])
    row = cursor.fetchone()
    return row[0] if row else None


def write_score(cursor, tile_hash, feature_name, score, model_version,
                timestamp):
    assert type(tile_hash) == str
    assert type(feature_name) == str
    assert type(score) == float
    assert type(model_version) == str
    assert type(timestamp) == str

    cursor.execute('''insert into scores
                      (tile_hash, feature_name, score, model_version,
                       timestamp)
                      values (?, ?, ?, ?, ?)
                      on conflict(tile_hash, feature_name) do
                      update set score=excluded.score,
                                 model_version=excluded.model_version,
                                 timestamp=excluded.timestamp
                   ''',
                   (tile_hash, feature_name, score, model_version, timestamp))


def remove_score(cursor, feature_name, tile_hash):
    cursor.execute('''delete from scores
                      where
                          feature_name = ?
                          and tile_hash = ?
                   ''',
                   [feature_name, tile_hash])


def set_has_feature(cursor, tile_hash, feature_name, has_feature):
    assert type(tile_hash) == str
    assert type(feature_name) == str
    assert type(has_feature) == bool

    cursor.execute('''insert into has_feature
                      (tile_hash, feature_name, has_feature)
                      values (?, ?, ?)
                   ''',
                   (tile_hash, feature_name, has_feature))


def all_tiles(cursor):
    cursor.execute('''select z, x, y
                      from last_update
                   ''')
    return cursor.fetchall()


def all_tile_hashes(cursor):
    cursor.execute('''select tile_hash
                      from tile_positions
                   ''')
    return cursor.fetchall()


def last_checked(cursor, z, x, y):
    cursor.execute('''select timestamp
                      from last_update
                      where z = ?
                            and x = ?
                            and y = ?
                   ''',
                   [z, x, y])
    row = cursor.fetchone()
    if row is None:
        return None

    return datetime.datetime.fromisoformat(row[0])


def mark_checked(cursor, z, x, y):
    assert type(z) == int
    assert type(x) == int
    assert type(y) == int

    now = datetime.datetime.now()
    timestamp = now.isoformat()
    cursor.execute('''insert into last_update
                      (z, x, y, timestamp)
                      values (?, ?, ?, ?)
                      on conflict do
                      update set timestamp=excluded.timestamp
                   ''',
                   [z, x, y, timestamp])


def training_tiles(cursor, feature_name):
    if feature.result_type(feature_name) == 'probability':
        cursor.execute('''select tile_hash, has_feature, 0
                          from training_set
                          natural join tile_positions
                          natural join has_feature
                          where feature_name = ?
                       ''',
                       [feature_name])
    elif feature.result_type(feature_name) == 'area':
        cursor.execute('''select tile_hash, score, 0
                          from training_set
                          natural join tile_positions
                          natural join true_score
                          where feature_name = ?
                       ''',
                       [feature_name])
    else:
        raise RuntimeError

    return cursor.fetchall()


def validation_tiles(cursor, feature_name):
    if feature.result_type(feature_name) == 'probability':
        cursor.execute('''select tile_hash, has_feature, score
                          from validation_set
                          natural join tile_positions
                          natural left join has_feature
                          natural left join scores
                          where feature_name = ?
                       ''',
                       [feature_name])
    elif feature.result_type(feature_name) == 'area':
        cursor.execute('''select tile_hash, true_score.score, scores.score
                          from validation_set
                          natural join tile_positions
                          natural left join true_score
                          natural left join scores
                          where feature_name = ?
                       ''',
                       [feature_name])
    else:
        raise RuntimeError
    return cursor.fetchall()


def validation_tiles_for_scoring(cursor, current_model, feature_name):
    cursor.execute('''select tile_hash, score
                      from validation_set
                      natural join tile_positions
                      natural left join scores
                      where
                          (model_version is null
                           or model_version != ?)
                          and feature_name = ?
                   ''',
                   [current_model, feature_name])
    return cursor.fetchall()


def set_true_score(cursor, tile_hash, feature_name, true_score):
    assert type(tile_hash) == str
    assert type(feature_name) == str
    assert type(true_score) == float

    cursor.execute('''insert into true_score
                      (tile_hash, feature_name, score)
                      values (?, ?, ?)
                   ''',
                   (tile_hash, feature_name, true_score))
