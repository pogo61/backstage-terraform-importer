#!/bin/python
import yaml
import hcl2
import os
import fnmatch


def extract_keys(dictionary):
    return [key for key in dictionary.keys()]


# Convert the Terraform HCL into JSON
def parsefile(tf_file):
    with open(tf_file, 'r') as file:
        tfdict = hcl2.load(file)

    return tfdict


# get the terraform variables defined in the file
def get_variables(path, file):
    vlist = []
    vjson = parsefile(path + '/' + file)
    main_keys = extract_keys(vjson)
    for varkey in main_keys:
        if varkey == 'variable':
            for key in vjson[varkey]:
                vlist.append(extract_keys(key)[0])

    return vlist


# define the Catalog-info.yaml file for the Environment entity
def define_environment(env, path):
    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='Environment',
        metadata=dict(
            name=env,
            description=env + ' environment'
        ),
        spec=dict(
            owner='platform-team',
            domain='infrastructure'
        )
    )

    with open(path + '/catalog-info.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)
    outfile.close()


# define the Catalog-info.yaml file for the ResourceComponent entity
def define_resource_component(tfjson, env_path, env):
    module_names = extract_keys(tfjson)
    module_path_keys = extract_keys(tfjson[module_names[0]])

    rel_path = tfjson[module_names[0]][module_path_keys[0]]
    path = env_path.rsplit('/', 1)[0] + '/' + rel_path.split('/', 1)[1]

    resource_list = []
    variable_list = []
    resource_file_list = []
    for file in os.listdir(path=path):
        if file.endswith(".tf") and ['main.tf', 'variables.tf', 'data_sources.tf', 'data.tf', 'local.tf', 'provider.tf'].count(file) == 0:
            resource_list.append('resource:' + file.split('.', 1)[0])
            resource_file_list.append(file)
        elif file.endswith(".tf") and (fnmatch.fnmatch(file, 'main.tf') or fnmatch.fnmatch(file, 'variables.tf')):
            variable_list = get_variables(path, file)

    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='ResourceComponent',
        metadata=dict(
            name=module_names[0],
            description=module_names[0] + ' terraform module'
        ),
        spec=dict(
            type='terraform',
            lifecycle='experimental',
            owner='platform-team',
            **({"providesVariables": variable_list}),
            **({"dependsOn": resource_list}),
            environment=[env]
        )
    )

    with open(path + '/catalog-info.yaml', 'w') as f:
        f.write('---\n')
    f.close()
    with open(path + '/catalog-info.yaml', 'a+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    # for each resource terraform file found in the module directory,
    # create a Resource entity in the ResourceComponents /catalog-info.yaml to match the dependsOn list
    for file in resource_file_list:
        resource_json = parsefile(path + '/' + file)
        for resource in resource_json['resource']:
            define_resource(resource, path)


# define the Catalog-info.yaml file for the Resource entity
def define_resource(tfjson, path):
    with open(path + '/catalog-info.yaml', 'a+') as f:
        f.write('---\n')
    f.close()

    resource_types = extract_keys(tfjson)
    resource_names = extract_keys(tfjson[resource_types[0]])

    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='Resource',
        metadata=dict(
            name=resource_types[0],
            description='resource ' + resource_types[0] + ' with name ' + resource_names[0],
        ),
        spec=dict(
            type='terraform',
            owner='platform-team'
        )
    )

    with open(path + '/catalog-info.yaml', 'a+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


# determine what's in Terraform pointed to by the user, and process accordingly
def create_catalog_defs(tf_name, env):
    env_dir = tf_name.rsplit('/', 1)[0]
    file_json = parsefile(tf_name)

    # define the catalog-info.yaml for the Environment entity
    define_environment(env, env_dir)

    # if the base Terraform has resources define in the base, define the catalog-info.yaml for the Resource entity/ies
    for resource in file_json['resource']:
        define_resource(resource, env_dir)

    # check to see if there are resource files in the base directory and create Resource def in the
    # catalog-info.yaml file for the Environment entity id there is
    for file in os.listdir(path=env_dir):
        if file.endswith(".tf") and ['main.tf', 'variables.tf', 'data_sources.tf', 'local.tf'].count(file) == 0:
            resource_file = parsefile(env_dir + '/' + file)
            for resource in resource_file['resource']:
                define_resource(resource, env_dir)

    # if the base Terraform has uses modules, define the catalog-info.yaml for the ResourceComponents entity/ies
    for module in file_json['module']:
        define_resource_component(module, env_dir, env)


if __name__ == "__main__":
    file_name = input('The name of the base "Environment" Terraform File to be parsed: ').lower()
    env_name = input('The name of the "Environment to be defined in Backstage": ').lower()

    if file_name is None:
        print("Please give a terraform file to parse.")
    elif env_name is None:
        print("Please give a name for the Environment.")
    else:
        create_catalog_defs(file_name, env_name)
