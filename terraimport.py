#!/bin/python
from pathlib import Path

import yaml
import hcl2
import os
import fnmatch


def was_value_inputted(value):
    try:
        if len(value) < 1:
            return False
        else:
            return True
    except TypeError:
        if type(value) == bool:
            return True
        else:
            return False



def was_yes_no_entered(value):
    if value == 'yes' or value == 'no':
        return True
    else:
        return False


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
def define_environment(env, path, dom_name, dom_new, grp_name, grp_new):
    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='Environment',
        metadata=dict(
            name=env,
            description=env + ' environment'
        ),
        spec=dict(
            owner=grp_name,
            domain=dom_name
        )
    )

    with open(path + '/catalog-info.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)
    outfile.close()

    if grp_new:
        group = dict(
            apiVersion='backstage.io/v1alpha1',
            kind='Group',
            metadata=dict(
                name=grp_name,
                description='The team responsible for environment ' + env
            ),
            spec=dict(
                type='business-unit',
                profile=dict(
                    displayName=grp_name
                ),
                parent='other',
                children=['backstage']
            )
        )

        with open(path + '/catalog-info.yaml', 'a+') as f:
            f.write('---\n')
        f.close()
        with open(path + '/catalog-info.yaml', 'a+') as outfile:
            yaml.dump(group, outfile, default_flow_style=False)

    if dom_new:
        domain = dict(
            apiVersion='backstage.io/v1alpha1',
            kind='Domain',
            metadata=dict(
                name=dom_name,
                description='Everything about Infrastructure'
            ),
            spec=dict(
                owner='backstage'
            )
        )

        with open(path + '/catalog-info.yaml', 'a+') as f:
            f.write('---\n')
        f.close()
        with open(path + '/catalog-info.yaml', 'a+') as outfile:
            yaml.dump(domain, outfile, default_flow_style=False)


# define the Catalog-info.yaml file for the ResourceComponent entity for the module defined by user
def define_resource_component(tfjson, env_path, env, group_name, ex_envs=None):
    if ex_envs is None:
        ex_envs = []
    module_names = extract_keys(tfjson)
    module_path_keys = extract_keys(tfjson[module_names[0]])
    rel_path = tfjson[module_names[0]][module_path_keys[0]]
    path_prefix = rel_path.split('/', 1)[0]
    resource_list = []
    variable_list = []
    resource_file_list = []
    envs = []

    # if the module is in a repo then it should be in the local '.terraform/' subdirectory  from a
    # 'terraform get' or 'terraform init'
    if ['github.com', 'git@github.com', 'bitbucket.org', 'git::https:', 'git::ssh:', 'hashicorp'].count(
            path_prefix) > 0:
        path = env_path.split('/')[1] + '/' + '.terraform/modules/' + module_names[0]
        if os.path.isfile(path + '/catalog-info.yaml'):
            print('The module already has a Backstage ResourceComponent definition - use this')
        else:
            print('The module should already have a Backstage ResourceComponent definition.')
            print('creating a temporary on in the ' + path + ' directory. Add this to your module repo!')
    elif 'terraform' in path_prefix:
        # process the Terraform Registry based module(s)
        path = env_path.split('/')[1] + '/' + '.terraform/modules/' + module_names[0]
        catalog_path = env_path.split('/')[1] + '/modules'
        if not os.path.exists(catalog_path):
            os.makedirs(catalog_path)
        terraform_module(path, catalog_path, env, module_names[0], None, ex_envs, group_name)
        return
    else:
        # assuming the module(s) are local
        path = env_path.rsplit('/', 1)[0] + '/' + rel_path.split('/', 1)[1]

    # check for resource and variables .tf files in the module folder
    try:
        for file in os.listdir(path=path):
            if file.endswith(".tf") and ['main.tf', 'variables.tf', 'data_sources.tf', 'data.tf', 'local.tf',
                                         'provider.tf'].count(file) == 0:
                resource_list.append('resource:' + file.split('.', 1)[0])
                resource_file_list.append(file)
            elif file.endswith(".tf") and (fnmatch.fnmatch(file, 'main.tf') or fnmatch.fnmatch(file, 'variables.tf')):
                variable_list = get_variables(path, file)
    except FileNotFoundError:
        print("This version of the utility doesn't support remote, or url based, modules")
        return

    if len(ex_envs) > 0:
        if env not in ex_envs:
            envs = [env] + ex_envs
        else:
            envs = ex_envs
    else:
        envs = [env]

    # create the ResourceComponent def for the module
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
            owner=group_name,
            providesVariables=variable_list,
            dependsO=resource_list,
            environment=envs
        )
    )

    # remove spec attributes that have no values
    spec = {}
    for key, value in data.items():
        if key == 'spec':
            spec = {
                k: v for k, v in value.items()
                if (v is not None) or (not v)
            }
    data.update(spec=spec)

    # prepend catalog template with yaml file separator
    # then insert the ResourceComponent definition
    with open(path + '/catalog-info.yaml', 'w') as f:
        f.write('---\n')
    f.close()
    with open(path + '/catalog-info.yaml', 'a+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    # for each file found in the module directory that has a resource defined,
    # create a Resource entity in the ResourceComponents /catalog-info.yaml to match the dependsOn list
    for file in resource_file_list:
        resource_json = parsefile(path + '/' + file)
        for resource in resource_json['resource']:
            define_resource(resource, path, group_name)


# function that processes the modules and submodules define in the Hashicorp registry
def terraform_module(path, cat_path, env, module_name, parent, ex_envs:list, group_name):
    module_list = []
    module_res_list = []
    module_var_list = []
    module_res_file_list = []
    submod_list = []
    envs = []

    # check to see if there aren't submodules and process if there are
    modules_path = path + '/modules'
    subcat_path = cat_path + '/modules'

    # recursively process the submodules of the module
    if Path(os.getcwd() + '/' + modules_path).is_dir():
        submod_list = os.listdir(path=Path(os.getcwd() + '/' + modules_path))
        for submod in submod_list:
            if not os.path.exists(subcat_path):
                os.makedirs(subcat_path)
            terraform_module(modules_path + '/' + submod, subcat_path, env, submod, module_name, ex_envs, group_name)

    # Once the recursion is finished and the submodule ResourceComponent created,
    # check if module has resource or variable files
    for file in os.listdir(path=path):
        if file.endswith(".tf") and ['main.tf', 'variables.tf', 'data_sources.tf', 'data.tf', 'local.tf',
                                     'provider.tf', 'versions.tf', 'outputs.tf'].count(file) == 0:
            module_res_list.append('resource:' + file.split('.', 1)[0])
        elif file.endswith(".tf") and fnmatch.fnmatch(file, 'variables.tf'):
            module_var_list = get_variables(path, file)
        elif file.endswith(".tf") and fnmatch.fnmatch(file, 'main.tf'):
            module_res_file_list.append(file)

    # create the list of subcomponent ResourceComponents used by the module (gotten from the recursion)
    for module in submod_list:
        module_list.append('resourcecomponent:' + module)

    # create the list of Resources used by the module if main.tf exists
    module_path = path + '/main.tf'
    if os.path.isfile(module_path):
        mod_json = parsefile(module_path)
        if mod_json.get('resource'):
            for resource in mod_json['resource']:
                res = extract_keys(resource)
                res_names = extract_keys(resource[res[0]])
                module_list.append('resource:' + res[0] + '-' + res_names[0])

    # create a list if parent is a single value
    if (parent is not None) and not (isinstance(parent, list)):
        subComp = parent
        parent = [parent]
    else:
        if (parent is not None):
            subComp = parent[0]
        else:
            subComp = None

    if len(ex_envs) > 0:
        if env not in ex_envs:
            envs = [env] + ex_envs
        else:
            envs = ex_envs
    else:
        envs = [env]

    # create the ResourceComponent def for the Terraform registry module
    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='ResourceComponent',
        metadata=dict(
            name=module_name,
            description=module_name + ' terraform module'
        ),
        spec=dict(
            parent=parent,
            subcomponentOf=subComp,
            type='terraform',
            lifecycle='experimental',
            owner=group_name,
            providesVariables=module_var_list,
            dependsOn=module_list,
            environment=envs
        )
    )

    # remove spec attributes that have no values
    spec = {}
    for key, value in data.items():
        if key == 'spec':
            spec = {
                k: v for k, v in value.items()
                if v is not None
            }
    data.update(spec=spec)

    # prepend catalog template with yaml file separator
    # then insert the ResourceComponent definition
    with open(cat_path + '/' + module_name + '-catalog-info.yaml', 'w') as f:
        f.write('---\n')
    f.close()
    with open(cat_path + '/' + module_name + '-catalog-info.yaml', 'a+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)

    # for each file found in the module directory that has a resource defined,
    # create a Resource entity in the ResourceComponents /catalog-info.yaml to match the dependsOn list
    for file in module_res_file_list:
        resource_json = parsefile(path + '/' + file)
        for resource in resource_json['resource']:
            define_resource(resource, cat_path, group_name, module_name)


# define the Catalog-info.yaml file for the Resource entity
def define_resource(tfjson, path, group_name, mod_name='none'):
    if mod_name != 'none':
        with open(path + '/' + mod_name + '-catalog-info.yaml', 'a+') as f:
            f.write('---\n')
    else:
        with open(path + '/catalog-info.yaml', 'a+') as f:
            f.write('---\n')
    f.close()

    resource_types = extract_keys(tfjson)
    resource_names = extract_keys(tfjson[resource_types[0]])

    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='Resource',
        metadata=dict(
            name=resource_types[0] + '-' + resource_names[0],
            description='resource ' + resource_types[0] + ' with name ' + resource_names[0],
        ),
        spec=dict(
            type='terraform',
            owner=group_name
        )
    )

    if mod_name != 'none':
        with open(path + '/' + mod_name + '-catalog-info.yaml', 'a+') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)
    else:
        with open(path + '/catalog-info.yaml', 'a+') as outfile:
            yaml.dump(data, outfile, default_flow_style=False)


# determine what's in Terraform pointed to by the user, and process accordingly
def create_catalog_defs(conf_dict):
    tf_name = conf_dict.get('env_path')
    env = conf_dict.get('environment')
    exist_envs  = conf_dict.get('existing_envs')
    domain_name = conf_dict.get('domain').get('name')
    domain_new = conf_dict.get('domain').get('new')
    group_name = conf_dict.get('group').get('name')
    group_new =  conf_dict.get('group').get('new')
    env_dir = tf_name.rsplit('/', 1)[0]
    file_json = parsefile(tf_name)

    # define the catalog-info.yaml for the Environment entity
    define_environment(env, env_dir, domain_name, domain_new, group_name, group_new)

    # if the base Terraform has resources define in the base, define the catalog-info.yaml for the Resource entity/ies
    if file_json.get('resource'):
        for resource in file_json['resource']:
            define_resource(resource, env_dir, group_name)

    # check to see if there are resource files in the base directory and create Resource def in the
    # catalog-info.yaml file for the Environment entity id there is
    for file in os.listdir(path=env_dir):
        if file.endswith(".tf") and ['main.tf', 'variables.tf', 'data_sources.tf', 'local.tf'].count(file) == 0:
            resource_file = parsefile(env_dir + '/' + file)
            for resource in resource_file['resource']:
                define_resource(resource, env_dir, group_name)

    # if the base Terraform has uses modules, define the catalog-info.yaml for the ResourceComponents entity/ies
    if file_json.get('module'):
        for module in file_json['module']:
            define_resource_component(module, env_dir, env, group_name, exist_envs)


def check_config(conf: dict):

    if not was_value_inputted(conf.get('env_path')):
        print("Please give a terraform file to parse.")
        return False

    if not was_value_inputted(conf.get('environment')):
        print("Please give a terraform file to parse.")
        return False

    if not was_value_inputted(conf.get('domain').get('name')):
        print("Please give a name for the Domain.")
        return False

    if not was_value_inputted(conf.get('domain').get('new')):
        print("Please indicate if the Domain is new or not.")
        return False

    if not was_value_inputted(conf.get('group').get('name')):
        print("Please give a name for the Group.")
        return False

    if not was_value_inputted(conf.get('group').get('new')):
        print("Please indicate if the Group is new or not.")
        return False

    return True


if __name__ == "__main__":
    print(' **NOTE** if the terraform uses repo-based modules, YOU MUST have run a "terraform get" before this utility')
    config_path = input('The path and name of the config file: ').lower()
    if not was_value_inputted(config_path):
        print("tell me where the config file is.")
        exit(1)

    # Read YAML config file
    with open(config_path, 'r') as stream:
        config = yaml.safe_load(stream)

    if check_config(config):
        create_catalog_defs(config)
    else:
        exit(1)
