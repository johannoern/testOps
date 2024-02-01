import json
import re
import os
import pystache

#NOTE this class is not only used for aws and also it is not only used for deploy but also build - therefore a change in the class name would be good

#NOTE if main hash has changed or does not exist handler has to be rewritten
#TODO also if the Handler needed to change as the main_function changes that also has to return false - may be store the hash of the orig main
def handler_implemented():
    return False

#LATER cannot build RequestStreamHandler only RequestHandler
def implement_handler(main_class, function_name, provider: list):
    #NOTE not to pretty really have to change the handler_implemented method
    aws_function_name = "handleRequest"
    gcp_function_name = "service"
    if handler_implemented():
        print("seems like the handler is already implemented and up to date")
        return main_class, aws_function_name, gcp_function_name
    package, output_type, inputs = parse_main(main_class, function_name)

    print("implementing handler")
    main_class_name = os.path.basename(main_class)
    main_folder = os.path.dirname(main_class)

    if main_class_name.endswith(".java"):
        main_class_name = main_class_name[:-5]

    if not inputs == "":
        inputs = "input"

    if output_type == "void":
        methodcall = f"{main_class_name}.{function_name}({inputs})"
        output_type = "String"
    else:
        methodcall = f"output = {main_class_name}.{function_name}({inputs})"

    #NOTE input types should ideally not be Object
    #unpacking object has to be done by the function - would be nicer if the code did that for you
    #input, aws, gcp
    context = {"package":package}
    for target in provider:
        context.update({target:{"package":package, "input_type": "Object", "output_type": output_type, "method_call": methodcall}})
    json.dumps(context, indent=4)
    with open(os.path.join('.', 'Baas', 'templates', 'request_handler.mustache'), "r") as template_file:
        template = template_file.read()
    
    handler_content = pystache.render(template, context)

    aws_handler = os.path.join(main_folder, "AWSRequestHandler.java")
    with open(aws_handler, "w") as handler:
        handler.write(handler_content)
    aws_handler = package + ".AWSRequestHandler"
    return aws_handler, aws_function_name, gcp_function_name

#NOTE may be the changes have to be taken back before building for google and azure
#mainly checking if fat jar is created - not pretty because it does not work if the jar task was already changed somehow
def adaptation_needed(project_path):
    build_file = os.path.join(project_path, 'build.gradle')
    with open(build_file, 'r') as file:
        content = file.read()
        if 'jar {' in content or 'jar{' in content:
            return False
        else:
            return True

def adapt_build_file(project_path, aws_handler):
    add_dependency(project_path, "implementation 'com.amazonaws:aws-lambda-java-core:1.2.3'")
    add_dependency(project_path, "implementation 'com.google.cloud.functions:functions-framework-api:1.1.0'")
    if not adaptation_needed(project_path):
        print("buildfile is up to date and will not be changed")
        return
    build_file = os.path.join(project_path, 'build.gradle')
    fat_jar = os.path.join('.', 'Baas', 'templates', 'fat_jar.mustache')
    with open(fat_jar, 'r') as add:
        template = add.read()
        content =  pystache.render(template, {"main_class":aws_handler})       
        with open(build_file, 'a') as build_file:
            build_file.write(content)

def add_dependency(project_path, dependency_string):
    build_file = os.path.join(project_path, 'build.gradle')

    with open(build_file, 'r') as file:
        build_gradle_content = file.read()

    # Check if the dependency already exists in the build.gradle file
    if dependency_string not in build_gradle_content:
        print(f"adding {dependency_string} to build.gradle")
        dependencies_index = build_gradle_content.find('dependencies {') + len('dependencies {')
        modified_build_gradle_content = (
            build_gradle_content[:dependencies_index] +
            f"\n    {dependency_string}" +
            build_gradle_content[dependencies_index:]
        )

        # Write the modified content back to the build.gradle file
        with open(build_file, 'w') as file:
            file.write(modified_build_gradle_content)
    else:
        print(f"{dependency_string} is already in build.gradle")

def parse_main(main_class, function_name):
    with open(main_class, "r") as main_class:
        content = main_class.read()
        package = re.search(r"\s*package\s*([^;\s]*)", content).group(1)
        #finds the input attributes and the out put type https://regex101.com/r/OezR0I/1
        pattern = rf" ([^\s]*) {function_name}.*\(([^\)]*)\)"
        function_match = re.search(pattern, content)
        output_type = function_match.group(1)
        inputs = function_match.group(2)
        return package, output_type, inputs
 