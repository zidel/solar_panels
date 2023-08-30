import datetime
import sqlite3


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

    def transaction(self):
        class Transaction(object):
            def __init__(self, cursor):
                self._cursor = cursor

            def __enter__(self):
                self._cursor.execute('begin')
                return self._cursor

            def __exit__(self, type, value, traceback):
                if type is None:
                    self._cursor.execute('commit')
                else:
                    self._cursor.execute('rollback')

        return Transaction(self._cursor())

    def _init_database(self):
        with self.transaction() as c:
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
                       natural left join scores
                       where
                           model_version is null
                           or (model_version != ?
                               and feature_name = ?)
                       {}
                    '''
        with self.transaction() as c:
            c.execute(query_fmt.format('count(*)', ''),
                      [current_model, feature_name])
            count = c.fetchone()[0]

            c.execute(query_fmt.format('tile_hash, score',
                                       'order by score desc limit ?'),
                      [current_model, feature_name, limit])
            tiles = c.fetchall()

        return (tiles, count)

    def tiles_for_review(self, feature_name, limit):
        only_validation_tiles = False
        review_most_likely = True

        query_condition = ''
        if only_validation_tiles:
            query_condition = '''and tile_hash in (
                                     select tile_hash
                                     from validation_set
                                     natural join tile_positions)
                              '''

        ordering = 'abs(score - 0.5) asc'
        if review_most_likely:
            ordering = 'score desc'

        with self.transaction() as c:
            model_fmt = '''select model_version
                           from scores
                           where
                               feature_name = ?
                               and timestamp in (
                                   select max(timestamp)
                                   from scores
                                   natural left join (
                                       select 1 as t, tile_hash
                                       from has_feature)
                                   where
                                       t is null
                                       and feature_name = ?
                                   {}
                               )
                        '''
            model_query = model_fmt.format(
                    query_condition)

            c.execute(model_query, [feature_name, feature_name])
            model_version = c.fetchone()
            if model_version is None:
                return []

            query_fmt = '''select tile_hash, z, x, y, score, model_version
                           from scores
                           natural left join (
                              select 1 as t, tile_hash
                              from has_feature)
                           natural join tile_positions
                           where t is null
                                 and feature_name = ?
                                 and score is not null
                                 and model_version = ?
                                 {}
                           order by {}
                           limit ?
                        '''
            query = query_fmt.format(
                    query_condition,
                    ordering,
                    )
            c.execute(query, [feature_name, model_version[0], limit])
            return c.fetchall()

    def tiles_with_solar(self):
        with self.transaction() as c:
            c.execute('''select tile_hash
                         from with_solar
                         where has_solar = True
                      ''')
            return c.fetchall()

    def remove_score(self, feature_name, tile_hash):
        with self.transaction() as c:
            c.execute('''delete from scores
                         where
                             feature_name = ?
                             and tile_hash = ?
                      ''',
                      [feature_name, tile_hash])


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
    cursor.execute('''insert into tile_positions
                      (tile_hash, z, x, y)
                      values (?, ?, ?, ?)
                      on conflict do nothing
                   ''',
                   (tile_hash, z, x, y))


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
    cursor.execute('''select tile_hash, has_feature, 0
                      from training_set
                      natural join tile_positions
                      natural join has_feature
                      where feature_name = ?
                   ''',
                   [feature_name])
    return cursor.fetchall()


def validation_tiles(cursor, feature_name):
    cursor.execute('''select tile_hash, has_feature, score
                      from validation_set
                      natural join tile_positions
                      natural left join has_feature
                      natural left join scores
                      where feature_name = ?
                   ''',
                   [feature_name])
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
