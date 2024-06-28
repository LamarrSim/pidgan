import pytest
import keras as k
import numpy as np

CHUNK_SIZE = int(1e4)
BATCH_SIZE = 500
EPOCHS = 5
LEARN_RATE = 0.001
ALPHA = 0.1

X = np.c_[
    np.random.uniform(-1, 1, size=CHUNK_SIZE),
    np.random.normal(0, 1, size=CHUNK_SIZE),
    np.random.exponential(5, size=CHUNK_SIZE),
]
Y = np.tanh(X[:, 0]) + 2 * X[:, 1] * X[:, 2]

model = k.Sequential()
try:
    model.add(k.layers.InputLayer(shape=(3,)))
except ValueError:
    model.add(k.layers.InputLayer(input_shape=(3,)))
for units in [16, 16, 16]:
    model.add(k.layers.Dense(units, activation="relu"))
model.add(k.layers.Dense(1))


@pytest.fixture
def scheduler():
    from pidgan.callbacks.schedulers import LearnRatePiecewiseConstDecay

    adam = k.optimizers.Adam(learning_rate=LEARN_RATE)
    sched = LearnRatePiecewiseConstDecay(
        optimizer=adam,
        boundaries=[25, 50],
        values=[LEARN_RATE, 5.0 * ALPHA * LEARN_RATE, ALPHA * LEARN_RATE],
        verbose=True,
        key="lr",
    )
    return sched


###########################################################################


def test_sched_configuration(scheduler):
    from pidgan.callbacks.schedulers import LearnRatePiecewiseConstDecay

    assert isinstance(scheduler, LearnRatePiecewiseConstDecay)
    assert isinstance(scheduler.name, str)
    assert isinstance(scheduler.optimizer, k.optimizers.Optimizer)
    assert isinstance(scheduler.boundaries, list)
    assert isinstance(scheduler.boundaries[0], int)
    assert isinstance(scheduler.values, list)
    assert isinstance(scheduler.values[0], float)
    assert len(scheduler.boundaries) == len(scheduler.values)
    assert isinstance(scheduler.verbose, bool)
    assert isinstance(scheduler.key, str)


def test_sched_use(scheduler):
    model.compile(optimizer=scheduler.optimizer, loss=k.losses.MeanSquaredError())
    train = model.fit(X, Y, batch_size=BATCH_SIZE, epochs=EPOCHS, callbacks=[scheduler])
    last_lr = float(f"{train.history['lr'][-1]:.8f}")
    assert last_lr == ALPHA * LEARN_RATE
