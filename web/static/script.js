function onload()
{
    get_next_to_check();

    document.addEventListener("keypress", key_handler);
}

function update_current_tile(tile)
{
    tile_hash = tile['tile_hash'];
    z = tile['z'];
    x = tile['x'];
    y = tile['y'];
    score = tile['score'];
    model_version = tile['model_version'];
    bbox_top = tile['top'];
    bbox_left = tile['left'];
    bbox_bottom = tile['bottom'];
    bbox_right = tile['right'];

    document.getElementById('tile_hash').textContent = `${tile_hash}`;
    document.getElementById('tile_z').textContent = `${z}`;
    document.getElementById('tile_x').textContent = `${x}`;
    document.getElementById('tile_y').textContent = `${y}`;
    document.getElementById('tile_bbox').textContent = `${bbox_top},${bbox_left},${bbox_bottom},${bbox_right}`;

    document.getElementById('review_tile').src = `/api/tiles/by-hash/${tile_hash}.jpeg`;
    document.getElementById('review_score').textContent = `${score}`
    document.getElementById('model_version').textContent = `${model_version}`

    document.getElementById('context_00').src = `/api/tiles/by-pos/${z}/${x - 1}/${y - 1}.jpeg`;
    document.getElementById('context_01').src = `/api/tiles/by-pos/${z}/${x + 0}/${y - 1}.jpeg`;
    document.getElementById('context_02').src = `/api/tiles/by-pos/${z}/${x + 1}/${y - 1}.jpeg`;

    document.getElementById('context_10').src = `/api/tiles/by-pos/${z}/${x - 1}/${y + 0}.jpeg`;
    document.getElementById('context_12').src = `/api/tiles/by-pos/${z}/${x + 1}/${y + 0}.jpeg`;

    document.getElementById('context_20').src = `/api/tiles/by-pos/${z}/${x - 1}/${y + 1}.jpeg`;
    document.getElementById('context_21').src = `/api/tiles/by-pos/${z}/${x + 0}/${y + 1}.jpeg`;
    document.getElementById('context_22').src = `/api/tiles/by-pos/${z}/${x + 1}/${y + 1}.jpeg`;
}

function get_next_to_check()
{
    document.getElementById('tile_hash').textContent = "";
    document.getElementById('tile_z').textContent = "";
    document.getElementById('tile_x').textContent = "";
    document.getElementById('tile_y').textContent = "";
    document.getElementById('tile_bbox').textContent = "";

    fetch("/api/review/next_tile")
        .then(function (response) {
            if (response.status == 200) {
                response.json().then(update_current_tile)
            } else if (response.status == 204) {
                // No tiles to check
            }
        })
}

function current_tile()
{
    tile_hash = document.getElementById('tile_hash').textContent;
    z = parseInt(document.getElementById('tile_z').textContent);
    x = parseInt(document.getElementById('tile_x').textContent);
    y = parseInt(document.getElementById('tile_y').textContent);

    bbox = document.getElementById('tile_bbox').textContent;
    bbox = bbox.split(',');

    return {
        'tile_hash': tile_hash,
        'z': z,
        'x': x,
        'y': y,
        'top': parseFloat(bbox[0]),
        'left': parseFloat(bbox[1]),
        'bottom': parseFloat(bbox[2]),
        'right': parseFloat(bbox[3]),
    }
}

function key_handler(event) {
    if (event.key === "j") {
        open_josm()
    } else if (event.key === "y") {
        submit_result('true');
    } else if (event.key === "n") {
        submit_result('false');
    } else if (event.key === "m") {
        submit_result('skip');
    }
}

function open_josm()
{
    tile = current_tile();
    bbox_top = tile['top'];
    bbox_left = tile['left'];
    bbox_bottom = tile['bottom'];
    bbox_right = tile['right'];
    fetch(`http://127.0.0.1:8111/load_and_zoom?left=${bbox_left}&right=${bbox_right}&top=${bbox_top}&bottom=${bbox_bottom}`)
}

function submit_result(result)
{
    tile = current_tile();

    data = {
        'tile_hash': tile['tile_hash'],
        'response': result,
    }

    fetch('/api/review/response', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
    })
    .then((r) => r.json())
    .then(get_next_to_check);
}
