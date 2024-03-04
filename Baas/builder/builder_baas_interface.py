from abc import ABC, abstractmethod

class builder_baas_interface(ABC):
    @abstractmethod
    def __init__(self, provider):
        pass
    
    @abstractmethod
    def handle_inputs(inputs):
        '''takes the inputs and writes the code which parses them for the function'''
        pass