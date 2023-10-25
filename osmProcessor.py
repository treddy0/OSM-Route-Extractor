import osmium
import sys
import csv
import os
import logging
import argparse


class pbfProcessor(osmium.SimpleHandler):
    def __init__(self, output_file, forceJoins=False, loggingLevel=20) -> None:
        """
        Args:
            forceJoins (bool, optional): should a join be forced when no perfect join available? 
            Defaults to True.
            loggingLevel (int, optional): python logging level. Defaults to 20.
        """
        # counters for number of routes
        self.totalRoutes = 0
        self.emptyRoutes = 0
        # counters for number of failed and succeeded way joins
        self.joinFails = 0
        self.joinSuc = 0
        # counts number of ways total in pbf
        self.totalWays = 0
        # counts number of ways that show up in routes
        self.usedWays = 0
        # dict that holds list of (lat, long) for nodes in order
        # key is way reference id
        self.ways = {}
        # argument for what happens when a perfect join is not possible
        self.forceJoins = forceJoins

        logging.basicConfig(filename="pbfProccesor.log",
                            format='%(asctime)s %(message)s',
                            filemode='w', force=True)
        self.logger = logging.getLogger()
        self.logger.setLevel(loggingLevel)

        # output file because memory constraints
        try:
            self.resFile = open(output_file, 'w+', newline='')
        except IOError:
            self.logger.error("Could not open stream to output file")
            sys.exit()
        self.writer = csv.writer(self.resFile, delimiter=' ', quotechar='|')
        super().__init__()

    def process(self, filename):
        """main processing function

        Args:
            filename (str): path to pbf file
        """
        self.apply_file(filename=filename, locations=True)

        self.logger.info("%s way joins failed" % self.joinFails)
        self.logger.info("%s way joins succeeded" % self.joinSuc)
        self.logger.info("%s total ways" % self.totalWays)
        self.logger.info("%s used ways" % self.usedWays)
        self.logger.info("%s total routes" % self.totalRoutes)
        self.logger.info("%s empty routes" % self.emptyRoutes)

        try:
            self.resFile.close()
        except IOError:
            self.logger.error("Could not close stream to output file")

    def way(self, w):
        # list to hold (long, lat) of nodes that make up way
        locations = []
        # increment counter
        self.totalWays += 1

        for n in w.nodes:
            try:
                locations.append((n.location.lat, n.location.lon))
            except:
                self.logger.warning("Way %s has an invalid node!" % w.id)

        # error check for empty ways
        if locations != []:
            self.ways[w.id] = locations
        else:
            self.logger.warning("Way %s has no nodes!" % w.id)

    def relation(self, rel):
        # only extracting roads
        if "type" in rel.tags and rel.tags['type'] == "route":
            if "route" in rel.tags and rel.tags['route'] == "road":
                self.totalRoutes += 1
                roadPoints = []
                # each route consists of ordered ways
                for w in rel.members:
                    # make sure the way is in the pbf
                    if w.ref in self.ways:
                        self.usedWays += 1
                        # no need to join on first way
                        if len(roadPoints) > 0:
                            # case where no reversal needed
                            if roadPoints[-1] == self.ways[w.ref][0]:
                                roadPoints += self.ways[w.ref]
                                self.joinSuc += 1
                            # case where reversal needed
                            elif roadPoints[-1] == self.ways[w.ref][-1]:
                                temp_way = self.ways[w.ref]
                                temp_way.reverse()
                                roadPoints += temp_way
                                self.joinSuc += 1
                            # case where no perfect join
                            else:
                                self.logger.debug(
                                    "error joining way %s into route %s" % (w.ref, rel.id))
                                if self.forceJoins:
                                    roadPoints += self.ways[w.ref]
                                self.joinFails += 1
                        else:
                            roadPoints += self.ways[w.ref]

                    else:
                        self.logger.debug(
                            "could not find way %s for route %s" % (w.ref, rel.id))
                # discard empty routes
                if len(roadPoints) > 0:
                    self.writer.writerow(roadPoints)
                else:
                    self.emptyRoutes += 1
                    self.logger.debug("route %s is empty" % w.ref)


class pbfProcessorLM(osmium.SimpleHandler):
    def __init__(self, output_file, forceJoins=False, loggingLevel=20) -> None:
        """
        Args:
            forceJoins (bool, optional): should a join be forced when no perfect join available? 
            Defaults to True.
            loggingLevel (int, optional): python logging level. Defaults to 20.
        """
        # counters for number of failed and succeeded way joins
        self.joinFails = 0
        # counts number of ways total in pbf
        self.joinSuc = 0
        # counts number of ways that show up in routes
        self.totalWays = 0
        # list of ways that actually appear in routes
        self.usedWays = []
        # dict that holds list of (lat, long) for nodes in order
        # key is way reference id
        self.ways = {}
        self.firstRun = True
        # argument for what happens when a perfect join is not possible

        self.forceJoins = forceJoins
        logging.basicConfig(filename="pbfProcessor.log",
                            format='%(asctime)s %(message)s',
                            filemode='w', force=True)
        self.logger = logging.getLogger()
        self.logger.setLevel(loggingLevel)
        self.writer = csv.writer(self.resFile, delimiter=' ', quotechar='|')
        try:
            self.resFile = open(output_file, 'w+', newline='')
        except OSError:
            self.logger.error("Could not open stream to output file")
            sys.exit()

        super().__init__()

    def process(self, filename):
        """main processing function

        Args:
            filename (str): path to pbf file
        """
        # the first run through extracts list of ways that actually appear in routes
        self.apply_file(filename=filename, locations=True)
        self.firstRun = False
        # the second run through ignores ways that do not appear in routes and gets result
        self.apply_file(filename=filename, locations=True)
        self.logger.info("%s way joins failed" % self.joinFails)
        self.logger.info("%s way joins succeeded" % self.joinSuc)
        self.logger.debug("%s total ways" % self.totalWays)
        self.logger.debug("%s used ways" % len(self.usedWays))
        try:
            self.resFile.close()
        except IOError:
            self.logger.error("Could not close stream to output file")

    def way(self, w):
        # do nothing on first run
        if not self.firstRun and w.id in self.usedWays:
            # list to hold (long, lat) of nodes that make up way
            locations = []
            for n in w.nodes:
                locations.append((n.location.lat, n.location.lon))
            if locations != []:
                self.ways[w.id] = locations
            else:
                self.logger.warning("Way %s has no nodes!" % w.id)

    def relation(self, rel):
        # only extract roads
        if "type" in rel.tags and rel.tags['type'] == "route":
            if "route" in rel.tags and rel.tags['route'] == "road":
                roadPoints = []
                # each route consists of ordered ways
                for w in rel.members:
                    # on first run just get ways that are used
                    if self.firstRun:
                        self.usedWays.append(w.ref)
                    # on second run join as normal
                    else:
                        if w.ref in self.ways:
                            # no need to join on first way
                            if len(roadPoints) > 0:
                                # case where no reversal needed
                                if roadPoints[-1] == self.ways[w.ref][0]:
                                    roadPoints += self.ways[w.ref]
                                    self.joinSuc += 1
                                # case where reversal needed
                                elif roadPoints[-1] == self.ways[w.ref][-1]:
                                    temp_way = self.ways[w.ref]
                                    temp_way.reverse()
                                    roadPoints += temp_way
                                    self.joinSuc += 1
                                # case where could not do a perfect join
                                else:
                                    self.logger.debug(
                                        "error joining way %s into route %s" % (w.ref, rel.id))
                                    if self.forceJoins:
                                        roadPoints += self.ways[w.ref]
                                    self.joinFails += 1
                            else:
                                roadPoints += self.ways[w.ref]
                    #   discard empty routes
                    if len(roadPoints) > 0:
                        self.writer.writerow(roadPoints)
                    else:
                        self.logger.warning("route %s is empty" % w.ref)


def main(args):
    if args.lowmem:
        processor = pbfProcessorLM(args.out_path, args.force, args.loglevel)
    else:
        processor = pbfProcessor(args.out_path, args.force, args.loglevel)
    processor.process(args.in_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("in_path", help="path to input file (osm.pbf)")
    parser.add_argument("out_path", help="path to output file (csv)")
    parser.add_argument("-f", "--force", action="store_true",
                        help="force joins")
    parser.add_argument("-lm", "--lowmem", action="store_true",
                        help="use low memory method")
    parser.add_argument("-l", "--loglevel", action="store", type=int, default=20,
                        help="logging level")
    args = parser.parse_args()
    main(args)
