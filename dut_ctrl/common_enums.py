"""
Common enumeration
"""

from enum import Enum

# ***************************************************************************************
# Helper classes
# ***************************************************************************************
class InterfaceOp(Enum):
    ATTACH = 1
    DETACH = 2

class AclCtrlPlaneType(Enum):
    """
    Enumeration used both for activating the correct if condition, 
    and the string name for the XML sent to the DUT.
    """
    EGRESS      = 1
    NNI_INGRESS = 2

class FrameType(Enum):
    """
    Enumeration for the different frame types that can be injected into BCM
    """
    L2_L3_FRAME = 1
    ICMP_FRAME  = 2

class InterfaceType(Enum):
    """
    Enumeration for the interface type
    """
    X_ETH       = 1
    CTRL_PLANE  = 2

class BcmrmErrors(Enum):
    OK        = 1
    DMA_ERROR = 2
