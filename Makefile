.PHONY : all flake8 web clean distclean


PYTHON_SRC := \
	database.py \
	download_tiles.py \
	model.py \
	score_tiles.py \
	train.py \
	util.py \
	web.py \


all : flake8 data/.score.marker
flake8 : .flake8.marker


.flake8.marker : $(PYTHON_SRC) Makefile
	flake8 $(PYTHON_SRC)
	touch .flake8.marker

data/.download.marker : download_tiles.py database.py Makefile
	python3 download_tiles.py --zoom 18
	touch data/.download.marker

data/.training.marker : data/.download.marker train.py Makefile
	python3 train.py --tensorboard --save-intermediate
	touch data/.training.marker

data/.score.marker : data/.training.marker Makefile
	python3 score_tiles.py
	touch data/.score.marker


web :
	python3 web.py


clean :
	$(RM) .flake8.marker
	$(RM) data/tiles.db
	$(RM) data/.download.marker
	$(RM) data/.training.marker
	$(RM) data/.score.marker

distclean : clean
	$(RM) -r data/
