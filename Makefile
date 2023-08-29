.PHONY : all flake8 web clean distclean compare_models


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


all : flake8 data/.score.marker
flake8 : .flake8.marker


.flake8.marker : $(PYTHON_SRC) Makefile
	flake8 $(PYTHON_SRC)
	touch .flake8.marker

data/.tiles_from_pop.marker : import_tiles_by_population.py database.py util.py Makefile
	python3 import_tiles_by_population.py --zoom 18
	touch data/.tiles_from_pop.marker

data/.download.marker : data/.tiles_from_pop.marker download_tiles.py database.py util.py Makefile
	python3 download_tiles.py
	touch data/.download.marker

data/model_bg1.hdf5 : data/.download.marker train.py Makefile
	python3 train.py --save-to=data/model_bg1.hdf5 --feature=solar

data/playground.hdf5 : data/.download.marker train.py Makefile
	python3 train.py --save-to=data/playground.hdf5 --feature=playground

data/.score.marker : data/model_bg1.hdf5 data/playground.hdf5 Makefile
	python3 score_tiles.py --load-model=data/model_bg1.hdf5
	python3 score_tiles.py --load-model=data/playground.hdf5 --feature=playground
	touch data/.score.marker


web :
	python3 web.py


clean :
	$(RM) .flake8.marker
	$(RM) data/.download.marker
	$(RM) data/.score.marker

distclean : clean
	$(RM) -r data/model_bg0.5.hdf5
	$(RM) -r data/model_bg1.hdf5
	$(RM) -r data/model_bg2.hdf5
	$(RM) -r data/model_bg3.hdf5
	$(RM) -r data/model.hdf5
