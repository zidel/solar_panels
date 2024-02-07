.PHONY : all flake8 web clean distclean compare_models test


PYTHON_SRC := \
	database.py \
	download_tiles.py \
	import_tiles_by_population.py \
	model.py \
	score_tiles.py \
	to_gpx.py \
	train.py \
	util.py \
	web.py \


all : flake8 test data/.score_solar.marker data/.score_playground.marker
flake8 : .flake8.marker


test :
	python3 -m unittest


.flake8.marker : $(PYTHON_SRC) Makefile
	flake8 $(PYTHON_SRC)
	touch .flake8.marker

data/.tile_import.marker : import_tiles.py database.py util.py population.csv buildings.csv businesses.csv Makefile
	python3 import_tiles.py --population
	python3 import_tiles.py --buildings
	python3 import_tiles.py --industrial_buildings
	python3 import_tiles.py --businesses
	touch data/.tile_import.marker

data/.download.marker : data/.tile_import.marker download_tiles.py database.py util.py Makefile
	python3 download_tiles.py
	touch data/.download.marker

data/solar.hdf5 : data/.download.marker train.py Makefile
	./in_container.sh python3 train.py --save-to=data/solar.hdf5 --feature=solar

data/large_solar.hdf5 : data/.download.marker train.py Makefile
	./in_container.sh python3 train.py --save-to=data/large_solar.hdf5 --feature=large_solar

data/playground.hdf5 : data/.download.marker train.py Makefile
	./in_container.sh python3 train.py --save-to=data/playground.hdf5 --feature=playground

data/.score_solar.marker : data/solar.hdf5 Makefile
	./in_container.sh python3 confusion_matrix.py --load-model=data/solar.hdf5 --feature=solar
	./in_container.sh python3 score_tiles.py --load-model=data/solar.hdf5 --feature=solar
	touch data/.score_solar.marker

data/.score_large_solar.marker : data/large_solar.hdf5 Makefile
	./in_container.sh python3 confusion_matrix.py --load-model=data/large_solar.hdf5 --feature=large_solar
	./in_container.sh python3 score_tiles.py --load-model=data/large_solar.hdf5 --feature=large_solar
	touch data/.score_large_solar.marker

data/.score_playground.marker : data/playground.hdf5 Makefile
	./in_container.sh python3 confusion_matrix.py --load-model=data/playground.hdf5 --feature=playground
	./in_container.sh python3 score_tiles.py --load-model=data/playground.hdf5 --feature=playground
	touch data/.score_playground.marker


web :
	python3 web.py


clean :
	$(RM) .flake8.marker
	$(RM) data/.tile_import.marker
	$(RM) data/.download.marker
	$(RM) data/.score_solar.marker
	$(RM) data/.score_playground.marker

distclean : clean
	$(RM) -r data/solar.hdf5
	$(RM) -r data/playground.hdf5
