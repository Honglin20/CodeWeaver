import os
from src.utils import helper

LR = 0.01
EPOCHS = 10

def train_model(data, lr=LR, epochs=EPOCHS):
    for epoch in range(epochs):
        loss = helper(data, lr)
    return loss

class Trainer:
    def __init__(self, lr=0.01):
        self.lr = lr

    def fit(self, data):
        return train_model(data, self.lr)
