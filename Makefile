.PHONY : all flake8 web clean distclean


PYTHON_SRC := \
	database.py \
	download_tiles.py \
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

data/.download.marker : download_tiles.py database.py Makefile
	python3 download_tiles.py --zoom 18
	touch data/.download.marker

data/.training.marker : data/.download.marker train.py Makefile
	python3 train.py
	touch data/.training.marker

data/.score.marker : data/.training.marker Makefile
	python3 score_tiles.py
	touch data/.score.marker


web :
	python3 web.py


compare_models :
	python3 train.py --model VGG19 --save-to data/vgg19.hdf5 --tensorboard=vgg19_bg2_lr-6
	python3 train.py --model VGG19_reduced --save-to data/vgg19_reduced.hdf5 --tensorboard=vgg19_reduced_bg2_lr-6
	python3 train.py --model VGG16 --save-to data/vgg16.hdf5 --tensorboard=vgg16_bg2_lr-6
	python3 train.py --model MobileNetV2 --save-to data/mobile_v2.hdf5 --tensorboard=mobilev2_bg2_lr-6
	echo
	python3 confusion_matrix.py --model data/vgg19.hdf5
	python3 confusion_matrix.py --model data/vgg19_reduced.hdf5
	python3 confusion_matrix.py --model data/vgg16.hdf5
	python3 confusion_matrix.py --model data/mobile_v2.hdf5


clean :
	$(RM) .flake8.marker
	$(RM) data/tiles.db
	$(RM) data/.download.marker
	$(RM) data/.training.marker
	$(RM) data/.score.marker

distclean : clean
	$(RM) -r data/
