#!/bin/python
import json
import yaml
import hcl2

def extract_keys(dictionary):
    return [key for key in dictionary.keys()]

def parsefile(tf_file):
    with open(tf_file, 'r') as file:
        tfdict = hcl2.load(file)

    return tfdict


def define_environment(env):
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

    with open('env-info.yaml', 'w') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


def define_resource(tfjson):
    with open('rc-info.yaml', 'a+') as f:
        f.write('---\n')
    f.close()

    resource_type = extract_keys(tfjson)
    # print(resource_type[0])

    resource_name = extract_keys(tfjson[resource_type[0]])
    # print(resource_name[0])

    data = dict(
        apiVersion='backstage.io/v1alpha1',
        kind='Resource',
        metadata=dict(
          name=resource_type[0],
          description='resource ' + resource_type[0] + ' with name ' + resource_name[0],
        ),
        spec=dict(
          type='terraform',
          owner='platform-team'
        )
    )

    with open('rc-info.yaml', 'a+') as outfile:
        yaml.dump(data, outfile, default_flow_style=False)


if __name__ == "__main__":
    file_name = input('The name of the "Environment" Terraform File to be parsed: ').lower()
    env_name = input('The name of the "Environment to be defined in Backstage": ').lower()

    if file_name is None:
        print("Please give a terraform file to parse.")
    elif env_name is None:
        print("Please give a name for the Environment.")
    else:
        file_json = parsefile(file_name)
        print(json.dumps(file_json, indent=4, default=str))
        define_environment(env_name)

    # if len(file_json[0]['module']) > 0:
    #     define_resource_component(file_json)

    for resource in file_json['resource']:
        define_resource(resource)
