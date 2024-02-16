import tensorflow as tf
import tensorflow.keras as keras


class BinaryIoU(keras.metrics.MeanIoU):
    def __init__(self):
        super().__init__(2)

    def update_state(self, y_true, y_pred, sample_weight=None):
        return super().update_state(
                tf.round(y_true),
                tf.round(y_pred),
                sample_weight)


def conv_layer(filters, kernel_size):
    return keras.layers.Conv2D(
            filters,
            kernel_size,
            activation='relu',
            padding='same',
            kernel_initializer='he_normal')


def pool(input_layer):
    return keras.layers.MaxPooling2D()(input_layer)


def custom(input_layer, _):
    processed = input_layer / 255.0

    conv_1 = conv_layer(64, 3)(processed)
    conv_2 = conv_layer(64, 3)(conv_1)
    pool_1 = pool(conv_2)

    conv_3 = conv_layer(128, 3)(pool_1)
    conv_4 = conv_layer(128, 3)(conv_3)
    pool_2 = pool(conv_4)

    conv_5 = conv_layer(256, 3)(pool_2)
    conv_6 = conv_layer(256, 3)(conv_5)
    conv_7 = conv_layer(256, 3)(conv_6)
    conv_8 = conv_layer(256, 3)(conv_7)
    pool_3 = pool(conv_8)

    conv_9 = conv_layer(512, 3)(pool_3)
    conv_10 = conv_layer(512, 3)(conv_9)
    conv_11 = conv_layer(512, 3)(conv_10)
    conv_12 = conv_layer(512, 3)(conv_11)
    pool_4 = pool(conv_12)

    conv_13 = conv_layer(512, 3)(pool_4)
    conv_14 = conv_layer(512, 3)(conv_13)
    conv_15 = conv_layer(512, 3)(conv_14)
    conv_16 = conv_layer(512, 3)(conv_15)
    pool_5 = pool(conv_16)

    # Return layers in a way that is compatible with Keras pretrained models.
    # The trainable parameter is just ignore, which is what we want since none
    # of the layers are pre-trained anyway.
    class Model(object):
        def __init__(self, output):
            self.output = output
            self.trainable = True
    return Model(pool_5)


def vgg19(input_layer, input_shape):
    processed = tf.keras.applications.vgg19.preprocess_input(input_layer)
    return keras.applications.vgg19.VGG19(
            include_top=False,
            input_tensor=processed,
            input_shape=input_shape,
            )


def vgg16(input_layer, input_shape):
    processed = tf.keras.applications.vgg16.preprocess_input(input_layer)
    return keras.applications.vgg16.VGG16(
            include_top=False,
            input_tensor=processed,
            input_shape=input_shape,
            )


def mobile_v2(input_layer, input_shape):
    processed = tf.keras.applications.mobilenet_v2.preprocess_input(
            input_layer)
    return keras.applications.mobilenet_v2.MobileNetV2(
            include_top=False,
            input_tensor=processed,
            input_shape=input_shape,
            )


def resnet_152_v2(input_layer, input_shape):
    processed = tf.keras.applications.resnet_v2.preprocess_input(input_layer)
    return keras.applications.resnet_v2.ResNet152V2(
            include_top=False,
            input_tensor=processed,
            input_shape=input_shape,
            )


def inception_resnet_v2(input_layer, input_shape):
    processed = tf.keras.applications.inception_resnet_v2.preprocess_input(
            input_layer)
    return keras.applications.inception_resnet_v2.InceptionResNetV2(
            include_top=False,
            input_tensor=processed,
            input_shape=input_shape,
            )


def get(model_type, result_type, weights_from=None, learning_rate=1e-4):
    input_shape = (256, 256, 3)
    inputs = keras.layers.Input(input_shape)

    factory, dense_width = {
            'custom': (custom, 1024),
            'VGG19': (vgg19, 1024),
            'VGG19_reduced': (vgg19, 512),
            'VGG16': (vgg16, 1024),
            'MobileNetV2': (mobile_v2, 1024),
            'ResNetV2': (resnet_152_v2, 512),
            'InceptionResNetV2': (inception_resnet_v2, 1024),
            }[model_type]
    feature_extraction = factory(inputs, input_shape)
    feature_extraction.trainable = False

    flatten = keras.layers.Flatten()(feature_extraction.output)
    dense_1 = keras.layers.Dense(dense_width, activation='relu')(flatten)
    dense_2 = keras.layers.Dense(dense_width, activation='relu')(dense_1)

    if result_type == 'probability':
        dense_3 = keras.layers.Dense(1, activation='sigmoid')(dense_2)
    elif result_type == 'area':
        dense_3 = keras.layers.Dense(1, activation='relu')(dense_2)

    model = keras.models.Model(inputs=inputs, outputs=dense_3)

    metrics = [
            keras.metrics.Recall(),
            keras.metrics.Precision(),
            ]
    model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=learning_rate),
            loss=keras.losses.BinaryCrossentropy(),
            metrics=metrics)

    if weights_from:
        model.load_weights(weights_from)

    return model
