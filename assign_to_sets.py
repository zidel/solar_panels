import argparse
import random

import database


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--database', default='data/tiles.db')
    parser.add_argument('--feature', default='solar')
    args = parser.parse_args()

    db = database.Database(args.database)
    with db.transaction() as c:
        c.execute('''select z, x, y
                     from last_update''')
        positions = [(args.feature, z, x, y)
                     for z, x, y
                     in c.fetchall()]

    random.shuffle(positions)
    print(f'Positions: {len(positions)}')
    validation_size = int(len(positions) / 10)
    validation = positions[:validation_size]
    print(f'Validation: {len(validation)}')
    training = positions[validation_size:]
    print(f'Training: {len(training)}')

    with db.transaction() as c:
        c.executemany('''insert into validation_set
                         (feature_name, z, x, y)
                         values (?, ?, ?, ?)''',
                      validation)
        c.executemany('''insert into training_set
                         (feature_name, z, x, y)
                         values (?, ?, ?, ?)''',
                      training)


if __name__ == '__main__':
    main()
