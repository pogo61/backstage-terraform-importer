# backstage-terraform-importer

On the back of the creation of the [Backstage IaC plugin](https://github.com/pogo61/Backstage-IaC-Plugin) 
where additional Catalogue Entities of Environment and ResourceComponent are defined to allow your IaC code
to be represented properly via the use of the Backstage standard catalog-info.yaml files.


This Python-based utility has been built to scan your Terraform files and auto-generating the requisite catalog-info.yaml files for:
* Environment
* ResourceComponent
* Resource

depending on what it finds.

---
**NOTE**
This is an opinionated utility and only supports modules defined in the same repo as the base terraform and reachable by the File system
Or where the module is defined in a remote repo or Terraform Registry, the 'terraform get' command must be run prior to this utility
--- 

## Using the utility
1. clone this repo to your local dev machine 
2. simply type `python3 terraimport.py` in the root directory of the cloned repo
3. you'll be prompted for a number of values
   1. the full path to the terraform file that forms the base of your IaC for an environment
   2. the name you call that environment
   3. the name of the Backstage domain that the Environment belongs to
   4. if this Domain is new for this Environment (it will create a Domain entity with the Environment if new)
   5. the name of the Backstage Group that owns the Environment 
   6. if this Group is new for this Environment (it will create a Group entity with the Environment if new)

```
 **NOTE** if the terraform uses repo-based modules, YOU MUST have run a "terraform get" before this utility
The path of the base "Environment" Terraform File to be parsed: ./tests/main.tf
The name of the "Environment" to be defined in Backstage: dev
The name of the "Domain" for the Environment: infrastructre
Is the Domain New? no
The name of the "Group" for the Environment: platform_team
Is the Group New? no
The module already has a Backstage ResourceComponent definition - use this
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
6. The output from the utility will be different depending where the module is defined:
   1. If, as per v1.0.0 of the utility, the module(s) are defined in teh same repo, or accessible on the same file System, then they'll be located as per 3.iii above
   2. If the modules are in different repos supported by Terraform as per [the Module Sources documentation](https://developer.hashicorp.com/terraform/language/modules/sources),and the catalog-info files don't exist, then they'll be placed into the folders for the source code under the `.terraform` folder. I.E. where the modules were downloaded by terraform via the `terraform get`. These files should really be added to the source repo's and used there. Because of this you'll receive this warning message:
   ```
   The module should already have a Backstage ResourceComponent definition
   creating a temporary on in the <path where the module code is> directory. Add this to your module repo!
   ```
   If, however, there already are catalog-info file(s) in those folders  you'll receive this message, and no files will be created: 
   ```
   The module already has a Backstage ResourceComponent definition - use this
   ```
   3. If you have modules defined that are from the Hashicorp Module Registry, then the utility will create a series of imbeaded `modules` folders as per the example in the `tests` folder in this repo. They will be prefixed with the module/submodule name. This is because these files, obviously, can't be added to the module's registry and need to be located somewhere for backstage to reference them. 

Once the utility is finished you can then define the created catalog-info.yaml files to your
Backstage instance in the same manner as defined in the [detailed Medium article](https://medium.com/@paulpogonoski/backstage-iac-support-392f34ea118e) that describes their use.
