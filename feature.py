_known_features = [
        'playground',
        'solar',
        'large_solar',
        'solar_area',
        ]


def overpass_query(feature):
    assert feature in _known_features

    if feature == 'playground':
        return '''[out:json][timeout:25];
                  area(id:3602978650)->.searchArea;
                  way["leisure"="playground"]
                     (area.searchArea);
                  out ids center qt; >; out skel qt;
               '''
    elif feature in ['solar', 'large_solar', 'solar_area']:
        return '''[out:json][timeout:25];
                  area(id:3602978650)->.searchArea;
                  way["power"="generator"]
                     ["generator:source"="solar"]
                     (area.searchArea);
                  out skel qt; >; out skel qt;
               '''


def result_type(feature):
    return {
            'large_solar': 'probability',
            'playground': 'probability',
            'solar_area': 'area',
            'solar': 'probability',
            }[feature]
