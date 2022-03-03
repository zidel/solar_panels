.PHONY : all flake8 web clean distclean compare_models


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


data/vgg19_lr3.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr3.hdf5 \
	                 --tensorboard=vgg19_bg2_lr-3 \
	                 --learning-rate=1e-3 \
	                 --step-count=250000 \
	                 --batch-size=256

data/vgg19_lr4_bg1.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr4_bg1.hdf5 \
	                 --tensorboard=vgg19_bg1_lr-4 \
	                 --learning-rate=1e-4 \
	                 --step-count=500000 \
	                 --background-scale=1 \
	                 --batch-size=256

data/vgg19_lr4_bg2.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr4_bg2.hdf5 \
	                 --tensorboard=vgg19_bg2_lr-4 \
	                 --learning-rate=1e-4 \
	                 --step-count=500000 \
	                 --background-scale=2 \
	                 --batch-size=256

data/vgg19_lr4_bg3.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr4_bg3.hdf5 \
	                 --tensorboard=vgg19_bg3_lr-4 \
	                 --learning-rate=1e-4 \
	                 --step-count=500000 \
	                 --background-scale=3 \
	                 --batch-size=256

data/vgg19_lr4_bg8.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr4_bg8.hdf5 \
	                 --tensorboard=vgg19_bg8_lr-4 \
	                 --learning-rate=1e-4 \
	                 --step-count=500000 \
	                 --background-scale=8 \
	                 --batch-size=256

data/vgg19_lr5.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr5.hdf5 \
	                 --tensorboard=vgg19_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=256

data/vgg19_lr6.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19 \
	                 --save-to data/vgg19_lr6.hdf5 \
	                 --tensorboard=vgg19_bg2_lr-6 \
	                 --learning-rate=1e-6 \
	                 --step-count=1000000 \
	                 --batch-size=256

data/vgg19_reduced.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG19_reduced \
	                 --save-to data/vgg19_reduced.hdf5 \
	                 --tensorboard=vgg19_reduced_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=1024

data/vgg16.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model VGG16 \
	                 --save-to data/vgg16.hdf5 \
	                 --tensorboard=vgg16_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=256

data/mobile_v2.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model MobileNetV2 \
	                 --save-to data/mobile_v2.hdf5 \
	                 --tensorboard=mobilev2_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=1024

data/resnet_v2.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model ResNetV2 \
	                 --save-to data/resnet_v2.hdf5 \
	                 --tensorboard=resnetv2_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=1024

data/inception_resnet_v2.hdf5 : train.py model.py Makefile
	TF_CPP_MIN_LOG_LEVEL=3 \
	python3 train.py --model InceptionResNetV2 \
	                 --save-to data/inception_resnet_v2.hdf5 \
	                 --tensorboard=inceptionv2_bg2_lr-5 \
	                 --learning-rate=1e-5 \
	                 --step-count=1000000 \
	                 --batch-size=2048

compare_models : data/vgg19_lr4_bg3.hdf5 \
	             data/vgg19_lr4_bg8.hdf5 \
	             data/resnet_v2.hdf5 \
	             data/inception_resnet_v2.hdf5 \
	             data/vgg19_lr3.hdf5 \
	             data/vgg19_lr4_bg1.hdf5 \
	             data/vgg19_lr4_bg2.hdf5 \
	             data/vgg19_lr5.hdf5 \
	             data/vgg19_lr6.hdf5 \
	             data/vgg19_reduced.hdf5 \
	             data/vgg16.hdf5 \
	             data/mobile_v2.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr3.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr4_bg1.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr4_bg2.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr4_bg3.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr4_bg8.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr5.hdf5
	python3 confusion_matrix.py --model VGG19 --load-model data/vgg19_lr6.hdf5
	python3 confusion_matrix.py --model VGG19_reduced --load-model data/vgg19_reduced.hdf5
	python3 confusion_matrix.py --model VGG16 --load-model data/vgg16.hdf5
	python3 confusion_matrix.py --model MobileNetV2 --load-model data/mobile_v2.hdf5
	python3 confusion_matrix.py --model ResNetV2 --load-model data/resnet_v2.hdf5
	python3 confusion_matrix.py --model InceptionResNetV2 --load-model data/inception_resnet_v2.hdf5


clean :
	$(RM) .flake8.marker
	$(RM) data/tiles.db
	$(RM) data/.download.marker
	$(RM) data/.training.marker
	$(RM) data/.score.marker

distclean : clean
	$(RM) -r data/
