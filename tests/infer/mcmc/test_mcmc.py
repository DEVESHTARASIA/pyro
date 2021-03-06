import logging

import torch
from torch.autograd import Variable

import pyro
import pyro.distributions as dist
from pyro import poutine
from pyro.infer import Marginal
from pyro.infer.mcmc.mcmc import MCMC
from pyro.infer.mcmc.trace_kernel import TraceKernel
from tests.common import assert_equal

logging.basicConfig()
# Change the logging level to DEBUG to see the output of the MCMC logger
logging.getLogger().setLevel(logging.ERROR)


class PriorKernel(TraceKernel):
    """
    Disregards the value of the current trace (or observed data) and
    samples a value from the model's prior.
    """
    def __init__(self, model):
        self.model = model
        self.data = None

    def setup(self, data):
        self.data = data

    def cleanup(self):
        self.data = None

    def initial_trace(self):
        return poutine.trace(self.model).get_trace(self.data)

    def sample(self, trace):
        return self.initial_trace()


def normal_normal_model(data):
    x = pyro.param('mu', Variable(torch.Tensor([0.0])))
    y = pyro.sample('x', dist.normal, mu=x, sigma=Variable(torch.Tensor([1])))
    pyro.sample('obs', dist.normal, mu=y, sigma=Variable(torch.Tensor([1])), obs=data)
    return y


def test_mcmc_interface():
    data = Variable(torch.Tensor([1.0]))
    kernel = PriorKernel(normal_normal_model)
    mcmc = MCMC(kernel=kernel, num_samples=800)
    marginal = Marginal(mcmc)
    samples = []
    for _ in range(400):
        samples.append(marginal.sample(data))
    sample_mean = torch.mean(torch.stack(samples), 0)
    sample_std = torch.std(torch.stack(samples), 0)
    assert_equal(sample_mean.data, torch.Tensor([0.0]), prec=0.08)
    assert_equal(sample_std.data, torch.Tensor([1.0]), prec=0.08)
