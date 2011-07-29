from pelita.datamodel import *
from pelita.game_master import *
from pelita.player import *
from pelita.viewer import *
import unittest

class TestGameMaster(unittest.TestCase):

    def test_basics(self):
        test_layout = (
        """ ##################
            #0#.  .  # .     #
            #2#####    #####1#
            #     . #  .  .#3#
            ################## """)

        game_master = GameMaster(test_layout, 4, 200)

        class BrokenViewer(AbstractViewer):
            pass

        class BrokenPlayer(AbstractPlayer):
            pass

        self.assertRaises(TypeError, game_master.register_viewer, BrokenViewer())
        self.assertRaises(TypeError, game_master.register_player, BrokenPlayer())
        self.assertRaises(IndexError, game_master.play)

class TestAbstracts(unittest.TestCase):

    def test_AbstractViewer(self):
        av = AbstractViewer()
        self.assertRaises(NotImplementedError, av.observe, None, None, None, None)

    def test_AbstractPlayer(self):
        ap = AbstractPlayer()
        self.assertRaises(NotImplementedError, ap.get_move, None)

class TestGame(unittest.TestCase):

    def test_game(self):

        test_start = (
            """ ######
                #0 . #
                #.. 1#
                ###### """)

        number_bots = 2

        # The problem here is that the layout does not allow us to specify a
        # different inital position and current position. When testing universe
        # equality by comparing its string representation, this does not matter.
        # But if we want to compare using the __eq__ method, but specify the
        # target as ascii encoded maze/layout we need to convert the layout to a
        # CTFUniverse and then modify the initial positions. For this we define
        # a closure here to quickly generate a target universe to compare to.
        # Also we adapt the score, in case food has been eaten

        def create_TestUniverse(layout):
            initial_pos = [(1, 1), (4, 2)]
            universe = create_CTFUniverse(layout, number_bots)
            for i, pos in enumerate(initial_pos):
                universe.bots[i].initial_pos = pos
            if not universe.maze.has_at(Food, (1, 2)):
                universe.teams[1]._score_point()
            if not universe.maze.has_at(Food, (2, 2)):
                universe.teams[1]._score_point()
            if not universe.maze.has_at(Food, (3, 1)):
                universe.teams[0]._score_point()
            return universe


        gm = GameMaster(test_start, number_bots, 200)
        gm.register_player(TestPlayer([east, east, east, south, stop, east]))
        gm.register_player(TestPlayer([west, west, west, stop, west, west]))

        gm.register_viewer(DevNullViewer())

        gm.play_round(0)
        test_first_round = (
            """ ######
                # 0. #
                #..1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_first_round), gm.universe)

        gm.play_round(1)
        test_second_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_second_round), gm.universe)

        gm.play_round(2)
        test_third_round = (
            """ ######
                #  . #
                #.0 1#
                ###### """)
        self.assertEqual(create_TestUniverse(test_third_round), gm.universe)

        gm.play_round(3)
        test_fourth_round = (
            """ ######
                #0 . #
                #. 1 #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fourth_round), gm.universe)

        gm.play_round(4)
        test_fifth_round = (
            """ ######
                # 0. #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_fifth_round), gm.universe)

        gm.play_round(5)
        test_sixth_round = (
            """ ######
                #  0 #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_sixth_round), gm.universe)


        # now play the full game
        gm = GameMaster(test_start, number_bots, 200)
        gm.register_player(TestPlayer([east, east, east, south, stop, east]))
        gm.register_player(TestPlayer([west, west, west, stop, west, west]))
        gm.play()
        test_sixth_round = (
            """ ######
                #  0 #
                #.1  #
                ###### """)
        self.assertEqual(create_TestUniverse(test_sixth_round), gm.universe)