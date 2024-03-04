
from Baas.builder.builder_baas_interface import builder_baas_interface


class AWS_builder_baas(builder_baas_interface):
    def __init__(self, provider):
        self._provider = provider

    def handle_inputs(self, results):
        print(f"results of matching: {results}")
        get_inputs = ""

        for result in results:
            get_inputs = f'{get_inputs}\t\t{result[0]} {result[1]} = ({result[0]}) input.get("{result[1]}");\n'


        return {self._provider:get_inputs}