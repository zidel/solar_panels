import datetime
import json
import requests
import sqlite3

import database
import util


def run_overpass_query(query):
    overpass_url = "https://overpass-api.de/api/interpreter"
    params = {'data': query}
    headers = {'User-Agent': 'zidel'}
    request = requests.get(overpass_url,
                           params=params,
                           headers=headers)
    request.raise_for_status()
    return request.text


def get_points_from_overpass():
    result = run_overpass_query(
    '''[out:json][timeout:25];
       area(id:3602978650)->.searchArea;
       way["power"="generator"]
          ["generator:type"="solar_photovoltaic_panel"]
          (area.searchArea);
       out ids center qt; >; out skel qt;
    ''')
    data = json.loads(result)

    for element in data['elements']:
        if 'center' in element:
            # {'type': 'way', 'id': 1023439043, 'center': {'lat': 59.9195945, 'lon': 10.632018}}
            yield element['center']
        elif 'lat' in element and 'lon' in element:
            # {'type': 'node', 'id': 9439577222, 'lat': 59.9362591, 'lon': 10.9199213}
            yield {'lat': element['lat'], 'lon': element['lon']}
        else:
            raise RuntimeError(str(element))


def main():
    db = database.Database('data/tiles.db')

    for point in get_points_from_overpass():
        xtile, ytile = util.deg2tile(point['lat'], point['lon'], 18)
        try:
            with db.transaction() as c:
                database.add_tile(c, 18, xtile, ytile)

                now = datetime.datetime.now()
                timestamp = now.isoformat()
                database.write_score(c, 18, xtile, ytile, 1.0, 'OSM', timestamp)

                c.execute('''delete from with_solar
                             where z = 18 and x = ? and y = ?''',
                          [xtile, ytile])
        except sqlite3.IntegrityError as e:
            pass

if __name__ == '__main__':
    main()
