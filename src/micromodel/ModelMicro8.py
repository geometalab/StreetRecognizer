# This model processes 32x32 pixel images and classifies them into
# 8 different classes. This model is based on CIFAR-10
# (https://www.cs.toronto.edu/~kriz/cifar.html).

from __future__ import print_function
import random
import os

import keras
from keras.preprocessing.image import ImageDataGenerator
from keras.models import Sequential
from keras.layers import Dense, Dropout, Activation, Flatten
from keras.layers import Conv2D, MaxPooling2D
import numpy
from PIL import Image

from micromodel.ModelMicro import ModelMicro
from micromodel.Types import DataPoint

class ModelMicro8(ModelMicro):
    CLASSES = [
        'asphalt',
        'gravel',
        # 'paved',
        'ground',
        # 'unpaved',
        'grass',
        'dirt',
        'concrete',
        'compacted',
        'fine_gravel'
    ]
    BATCH_SIZE = 32
    NUM_CLASSES = 8
    EPOCHS = 100
    STEPS_PER_EPOCH = 100
    DATA_AUGMENTATION = True

    def __init__(self, model_path: str):
        super().__init__(
            num_classes=self.NUM_CLASSES,
            model_path=model_path
        )

    @classmethod
    def create_untrained(cls, model_name: str) -> "ModelMicro8":
        save_dir = os.path.join(os.getcwd(), 'micromodel', 'saved_models', 'micro8')
        model_path = os.path.join(save_dir, model_name)

        os.makedirs(save_dir, exist_ok=True)

        model = Sequential()
        model.add(Conv2D(32, (3, 3), padding='same', input_shape=(32, 32, 3)))
        model.add(Activation('relu'))
        model.add(Conv2D(32, (3, 3)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))

        model.add(Conv2D(64, (3, 3), padding='same'))
        model.add(Activation('relu'))
        model.add(Conv2D(64, (3, 3)))
        model.add(Activation('relu'))
        model.add(MaxPooling2D(pool_size=(2, 2)))
        model.add(Dropout(0.25))

        model.add(Flatten())
        model.add(Dense(512))
        model.add(Activation('relu'))
        model.add(Dropout(0.5))
        model.add(Dense(cls.NUM_CLASSES))
        model.add(Activation('softmax'))

        model.save(model_path)
        print('Saved untrained model at {0}'.format(model_path))

        return ModelMicro8(model_path=model_path)

    @classmethod
    def load(cls, model_name: str) -> "ModelMicro8":
        save_dir = os.path.join(os.getcwd(), 'micromodel', 'saved_models', 'micro8')
        return ModelMicro8(model_path=os.path.join(save_dir, model_name))

    def train(self, micro_image_dir: str, train_percentage: float):
        if not os.path.exists(micro_image_dir):
            raise ValueError('Directory {0} not found'.format(micro_image_dir))

        input_dir = os.path.join(os.getcwd(), micro_image_dir)
        print('Reading sample images from {0}'.format(input_dir))

        data = []
        for surface in os.listdir(input_dir):
            dir_full = os.path.join(micro_image_dir, surface)
            if not os.path.isdir(dir_full):
                print('\t{0} is not a directory, skipping...'.format(dir_full))
                continue

            if surface not in self.CLASSES:
                print('\t{0} is not in selected classes, skipping...'.format(surface))
                continue

            for sample in os.listdir(dir_full):
                if not os.path.splitext(sample)[1] == ".png":
                    print('\t{0} is not a PNG image, skipping...'.format(sample))
                    continue

                image = Image.open(os.path.join(dir_full, sample))
                data.append(DataPoint(
                    measurements=list(image.getdata()),
                    response=self._map_surface_to_int(surface)
                ))

        random.shuffle(data)
        splitpoint = int(len(data) * train_percentage)

        x_train = []
        y_train = []
        x_test = []
        y_test = []
        for i, sample in enumerate(data):
            if i < splitpoint:
                x_train.append(sample.measurements)
                y_train.append(sample.response)
            else:
                x_test.append(sample.measurements)
                y_test.append(sample.response)

        x_train = numpy.array(x_train).reshape((len(x_train), 32, 32, 3))
        y_train = numpy.array(y_train)
        x_test = numpy.array(x_test).reshape((len(x_test), 32, 32, 3))
        y_test = numpy.array(y_test)

        print('total samples: {0}'.format(len(data)))
        print('x_train shape: {0}'.format(x_train.shape))
        print('x_test  shape: {0}'.format(x_test.shape))

        self._train(
            x_train=x_train,
            y_train=y_train,
            x_test=x_test,
            y_test=y_test
        )

    def _train(self, x_train: [], y_train: [], x_test: [], y_test: []):
        # Convert class vectors to binary class matrices.
        y_train = keras.utils.to_categorical(y_train, self.NUM_CLASSES)
        y_test = keras.utils.to_categorical(y_test, self.NUM_CLASSES)

        model = keras.models.load_model(self._model_path)

        # initiate RMSprop optimizer
        opt = keras.optimizers.rmsprop(lr=0.0001, decay=1e-6)

        # Let's train the model using RMSprop
        model.compile(loss='categorical_crossentropy',
                    optimizer=opt,
                    metrics=['accuracy'])

        x_train = x_train.astype('float32')
        x_test = x_test.astype('float32')
        x_train /= 255
        x_test /= 255

        if not self.DATA_AUGMENTATION:
            print('Not using data augmentation.')
            model.fit(x_train, y_train,
                    batch_size=self.BATCH_SIZE,
                    epochs=self.EPOCHS,
                    validation_data=(x_test, y_test),
                    shuffle=True)
        else:
            print('Using real-time data augmentation.')
            # This will do preprocessing and realtime data augmentation:
            datagen = ImageDataGenerator(
                featurewise_center=False,  # set input mean to 0 over the dataset
                samplewise_center=False,  # set each sample mean to 0
                featurewise_std_normalization=False,  # divide inputs by std of the dataset
                samplewise_std_normalization=False,  # divide each input by its std
                zca_whitening=False,  # apply ZCA whitening
                zca_epsilon=1e-06,  # epsilon for ZCA whitening
                rotation_range=0,  # randomly rotate images in the range (degrees, 0 to 180)
                # randomly shift images horizontally (fraction of total width)
                width_shift_range=0.1,
                # randomly shift images vertically (fraction of total height)
                height_shift_range=0.1,
                shear_range=0.,  # set range for random shear
                zoom_range=0.,  # set range for random zoom
                channel_shift_range=0.,  # set range for random channel shifts
                # set mode for filling points outside the input boundaries
                fill_mode='nearest',
                cval=0.,  # value used for fill_mode = "constant"
                horizontal_flip=True,  # randomly flip images
                vertical_flip=False,  # randomly flip images
                # set rescaling factor (applied before any other transformation)
                rescale=None,
                # set function that will be applied on each input
                preprocessing_function=None,
                # image data format, either "channels_first" or "channels_last"
                data_format=None,
                # fraction of images reserved for validation (strictly between 0 and 1)
                validation_split=0.0)

            # Compute quantities required for feature-wise normalization
            # (std, mean, and principal components if ZCA whitening is applied).
            datagen.fit(x_train)

            # Fit the model on the batches generated by datagen.flow().
            model.fit_generator(datagen.flow(x_train, y_train,
                                            batch_size=self.BATCH_SIZE),
                                epochs=self.EPOCHS,
                                steps_per_epoch=self.STEPS_PER_EPOCH,
                                validation_data=(x_test, y_test),
                                workers=4)

        # Save model and weights
        model.save(self._model_path)
        print('Saved trained model at {0}'.format(self._model_path))

        # Score trained model.
        scores = model.evaluate(x_test, y_test, verbose=1)
        print('Test loss:', scores[0])
        print('Test accuracy:', scores[1])

    @staticmethod
    def _map_surface_to_int(surface: str) -> int:
        mapping = {
            'asphalt': 0,
            'gravel': 1,
            #'paved': 2,
            'ground': 2,
            #'unpaved': 4,
            'grass': 3,
            'dirt': 4,
            'concrete': 5,
            'compacted': 6,
            'fine_gravel': 7
        }
        return mapping[surface]
    def _map_int_to_surface(self, number:int) -> str:
        mapping = {
            0: 'asphalt',
            1: 'gravel' ,
            2: 'ground',
            3: 'grass',
            4: 'dirt',
            5: 'concrete',
            6: 'compacted',
            7: 'fine_gravel'
        }
        return mapping[number]
