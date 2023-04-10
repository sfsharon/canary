import logging
logging.basicConfig(
                    format='%(asctime)s.%(msecs)03d [%(filename)s line %(lineno)d] %(levelname)-8s %(message)s',                       
                    level=logging.INFO,
                    datefmt='%H:%M:%S')

import pytest

class MyThing():
    def open(self):
        logging.info("Open MyThing")
    def do_stuff(self):
        logging.info("do_stuff doing things")
    def close(self):
        logging.info("Close MyThing")
        
# @pytest.fixture(scope="module")
# @pytest.fixture()
@pytest.fixture(scope="session")
def MyThing_client():
    logging.info ("** Start: MyThing_client")
    my_thing = MyThing()
    yield my_thing
    logging.info ("** Stopping: MyThing_client")
    my_thing.close()

def test_my_investigate(MyThing_client):
    logging.info("*** Start: test_my_investigate")
    MyThing_client.do_stuff()
    logging.info("*** End: test_my_investigate")

def test_my_investigate_2(MyThing_client):
    logging.info("*** Start: test_my_investigate_2")
    MyThing_client.do_stuff()
    logging.info("*** End: test_my_investigate_2")