import sqlite3


class Database(object):
    def __init__(self, path):
        self._db = sqlite3.Connection(path)
        self._init_database()

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
            c.execute('''create table if not exists tiles (
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             primary key (z, x, y))
                      ''')
            c.execute('''create table if not exists with_solar (
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             has_solar bool not null,
                             primary key (z, x, y)
                             foreign key (z, x, y) references tiles)
                      ''')
            c.execute('''create table if not exists scores (
                             z integer not null,
                             x integer not null,
                             y integer not null,
                             score real not null,
                             primary key (z, x, y),
                             foreign key (z, x, y) references tiles)
                      ''')

    def tiles(self):
        tiles = []
        with self.transaction() as c:
            c.execute('''select z, x, y
                         from tiles
                         natural left join scores
                         where score is null
                      ''')
            tiles += c.fetchall()

            c.execute('''select z, x, y
                         from tiles
                         natural left join scores
                         natural left join with_solar
                         where score is not null
                         order by has_solar asc, score desc
                      ''')
            tiles += c.fetchall()

        return tiles

    def trainable(self):
        with self.transaction() as c:
            c.execute('''select z, x, y, has_solar
                         from with_solar
                      ''')
            return c.fetchall()

    def training_candidates(self, limit):
        with self.transaction() as c:
            c.execute('''select z, x, y, score
                         from scores
                         natural left join (
                            select 1 as t, z, x, y
                            from with_solar)
                         where t is null
                               and score is not null
                         order by abs(score - 0.5) asc
                         limit ?
                      ''',
                      (limit,))
            return c.fetchall()


def add_tile(cursor, z, x, y):
    assert(type(z) == int)
    assert(type(x) == int)
    assert(type(y) == int)

    cursor.execute('''insert into tiles
                      (z, x, y)
                      values (?, ?, ?)
                      on conflict do nothing
                   ''',
                   (z, x, y))


def write_score(cursor, z, x, y, score):
    assert(type(z) == int)
    assert(type(x) == int)
    assert(type(y) == int)
    assert(type(score) == float)

    cursor.execute('''insert into scores
                      (z, x, y, score)
                      values (?, ?, ?, ?)
                      on conflict(z, x, y) do
                      update set score=excluded.score
                   ''',
                   (z, x, y, score))


def set_has_solar(cursor, z, x, y, has_solar):
    assert(type(z) == int)
    assert(type(x) == int)
    assert(type(y) == int)
    assert(type(has_solar) == bool)

    cursor.execute('''insert into with_solar
                      (z, x, y, has_solar)
                      values (?, ?, ?, ?)
                   ''',
                   (z, x, y, has_solar))
