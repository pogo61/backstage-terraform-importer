# backstage-terraform-importer

On the back of the creation of the [Backstage IaC plugin](https://github.com/pogo61/Backstage-IaC-Plugin) 
where additional Catalogue Entities of Environment and ResourceComponent are defined to allow your IaC code
to be represented properly via the use of the Backstage standard catalog-info.yaml files.


This Python-based utility has been built to scan your Terraform files and auto-generating the requisite catalog-info.yaml files for:
* Environment
* ResourceComponent
* Resource

depending on what it finds.

## Using the utility
1. clone this repo to your local dev machine 
2. simply type `python3 terraimport.py` in the root directory of the cloned repo
3. you'll be prompted for two values
   1. the full path to the terraform file that forms the base of your IaC for an environment
   2. the name you call that environment

```
The name of the base "Environment" Terraform File to be parsed: /Users/paulpog/IdeaProjects/ecs-cluster-terraform/deployment/dev/main.tf
The name of the "Environment to be defined in Backstage": dev

Process finished with exit code 0
```
                                                             
 The utility will then do the following:
1. Parse that base terraform file and determine whether it uses and modules and/or resources
2. Create a catalog-info.yaml in the same folder that the base terraform file is in. This defines the Environment Entity
3. For every Module it uses, the utility will go to where the module is defined
   1. check the directory for resource terraform files and define a list of them
   2. check the directory for main.tf, or variables.tf files and define a list on input variables
   3. Define catalog-info.yaml in each of the modules folders that define 
      1. the ResourceComponent entity for the  module that includes the lists of variables and resources
      2. the Resource entity for every resource in the resource list
4. if there are resources in the base terraform file it will append Resource entity definitions for those in the catalog-info.yaml in the same folder that the base terraform file
5. if there are resource terraform files in the folder of the base terraform file it will append Resource entity definitions for those in the catalog-info.yaml in the same folder that the base terraform file

Once the utility is finished you can then define the created catalog-info.yaml files to your
Backstage instance in the same manner as defined in the [detailed Medium article](https://medium.com/@paulpogonoski/backstage-iac-support-392f34ea118e) that describes their use.
