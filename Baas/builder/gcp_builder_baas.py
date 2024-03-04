
from Baas.builder.builder_baas_interface import builder_baas_interface


class GCP_builder_baas(builder_baas_interface):
    def __init__(self, provider):
        self._provider = provider

    def handle_inputs(self, results):
        get_inputs = "\t\tType mapType = new TypeToken<Map<String, Object>>() {}.getType();\n"
        get_inputs = get_inputs + "\t\tMap<String, Object> requestData = gson.fromJson(requestBody, mapType);\n"

        for result in results:
            if any(substring in result[0] for substring in ["int", "Integer"]):
                get_inputs = f'{get_inputs}\t\tDouble {result[1]}_double = (Double) requestData.get("{result[1]}");\n\t\t{result[0]} {result[1]} = {result[1]}_double.intValue();\n'
                continue
            get_inputs = f'{get_inputs}\t\t{result[0]} {result[1]} = ({result[0]}) requestData.get("{result[1]}");\n'


        return {self._provider:get_inputs}