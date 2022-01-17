.PHONY : all flake8 clean distclean


PYTHON_SRC := \
	database.py \
	download_tiles.py \
	init_database.py \
	model.py \
	review.py \
	score_tiles.py \
	train.py \
	util.py \


all : flake8 data/.score.marker
flake8 : .flake8.marker


.flake8.marker : $(PYTHON_SRC) Makefile
	flake8 $(PYTHON_SRC)
	touch .flake8.marker

data/.init_db.marker : init_database.py database.py population.csv Makefile
	python3 init_database.py --zoom 18
	touch data/.init_db.marker

data/.download.marker : data/.init_db.marker download_tiles.py database.py Makefile
	python3 download_tiles.py
	touch data/.download.marker

data/.training.marker : data/.download.marker train.py Makefile
	python3 train.py
	touch data/.training.marker

data/.score.marker : data/.training.marker Makefile
	python3 score_tiles.py
	touch data/.score.marker


clean :
	$(RM) .flake8.marker
	$(RM) data/.init_db.marker
	$(RM) data/tiles.db
	$(RM) data/.download.marker
	$(RM) data/.training.marker
	$(RM) data/.score.marker

distclean : clean
	$(RM) -r data/
