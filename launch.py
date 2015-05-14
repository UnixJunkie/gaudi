#!/usr/bin/python

##############
# GAUDIasm: Genetic Algorithms for Universal
# Design Inference and Atomic Scale Modeling
# Authors:  Jaime Rodriguez-Guerra Pedregal
#            <jaime.rodriguezguerra@uab.cat>
#           Jean-Didier Marechal
#            <jeandidier.marechal@uab.cat>
# Web: https://bitbucket.org/jrgp/gaudi
##############

"""
launch -- Run GAUDI essays
==========================

This script is the main hub for launching GAUDI essays.

It sets up the configuration environment needed by DEAP (responsible for the GA)
and ties it up to the GAUDI custom classes that shape up the invididuals and
objectives. All in a loosely-coupled approach based on Python modules called on-demand.

*Usage*. Call it from Chimera with a GAUDI input file as the first and only argument.
Using `nogui` flag is recommended to speed up the calculations:

    cd /path/to/gaudi/installation/directory/
    /path/to/chimera/bin/chimera --nogui --script "launch.py /path/to/gaudi.yaml"

Read `README.md` for additional details on useful aliases.

.. todo::

    DEAP default algorithm is nice, but we will be needing some custom features. For
    example, handle KeyboardInterrupt not to lose the population, and so on.
"""

# Python
import sys
import os
import numpy
from time import strftime
from collections import OrderedDict
# External dependencies
import deap
from deap import creator, tools, base, algorithms
import yaml
# GAUDI
import gaudi


def main(cfg):
    gaudi.plugin.import_plugins(*cfg.genes)
    gaudi.plugin.import_plugins(*cfg.objectives)

    # DEAP setup: Fitness, Individuals, Population
    toolbox = deap.base.Toolbox()
    toolbox.register("call", (lambda fn, *args, **kwargs: fn(*args, **kwargs)))
    toolbox.register("individual", toolbox.call, gaudi.base.Individual, cfg)
    toolbox.register(
        "population", deap.tools.initRepeat, list, toolbox.individual)
    population = toolbox.population(n=cfg.ga.pop)

    toolbox.register("evaluate", lambda ind: ind.evaluate())
    toolbox.register("mate", (lambda ind1, ind2: ind1.mate(ind2)))
    toolbox.register(
        "mutate", (lambda ind, indpb: ind.mutate(indpb)), indpb=cfg.ga.mut_indpb)
    toolbox.register("similarity", (lambda ind1, ind2: ind1.similar(ind2)))
    toolbox.register("select", deap.tools.selNSGA2)

    if cfg.ga.history:
        history = deap.tools.History()
        # Decorate the variation operators
        toolbox.decorate("mate", history.decorator)
        toolbox.decorate("mutate", history.decorator)
        history.update(population)

    paretofront = deap.tools.ParetoFront(toolbox.similarity)
    stats = deap.tools.Statistics(lambda ind: ind.fitness.values)
    numpy.set_printoptions(precision=cfg.general.precision)
    stats.register("avg", numpy.mean, axis=0)
    stats.register("min", numpy.min, axis=0)
    stats.register("max", numpy.max, axis=0)
    population, log = deap.algorithms.eaMuPlusLambda(population, toolbox,
                                                     mu=int(cfg.ga.mu * cfg.ga.pop), lambda_=int(cfg.ga.lambda_ * cfg.ga.pop),
                                                     cxpb=cfg.ga.cx_pb, mutpb=cfg.ga.mut_pb,
                                                     ngen=cfg.ga.gens, stats=stats, halloffame=paretofront)

    return population, log, paretofront

if __name__ == "__main__":
    # Parse input
    try:
        cfg = gaudi.parse.Settings(sys.argv[1])
    except IndexError:
        raise ValueError("Input file not provided")
    except IOError:
        raise IOError("Specified input file was not found")

    try:
        os.makedirs(cfg.general.outputpath)
    except OSError:
        if not os.path.isdir(cfg.general.outputpath):
            raise
    # log = gaudi.parse.enable_logging(cfg.general.outputpath)
    # log.info("Starting GAUDI job")
    # log.info("Opened input file '{}'".format(sys.argv[1]))
    # log.info("Scores:", ', '.join(o.name for o in cfg.objectives))
    pop, log, paretofront = main(cfg)

    results = OrderedDict()
    results['GAUDI.objectives'] = [
        '{} ({})'.format(obj.name, obj.type) for obj in cfg.objectives]
    results['GAUDI.results'] = OrderedDict()
    for i, ind in enumerate(paretofront):
        filename = ind.write(i)
        results['GAUDI.results'][filename] = list(ind.fitness.values)

    out = open(cfg.general.outputpath + cfg.general.name + '.gaudi.yaml', 'w+')
    print >> out, '# Generated by GAUDI on {}'.format(
        strftime("%Y-%m-%d %H:%M:%S"))
    print >> out, yaml.dump(results, default_flow_style=False)
    out.close()
