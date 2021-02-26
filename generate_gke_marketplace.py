import os
import time

##################################################################################################################

# this is needed to find the correct files
KIND_PSP = lambda x: "psp" in x
KIND_CRD = lambda x: "crd" in x
KIND_APM = lambda x: "apm" in x
KIND_ONEAGENT = lambda x: "oneagent" in x

# this is needed to find the correct files
DYNATRACE_ONEAGENT_OPERATOR = "name: dynatrace-oneagent-operator\n"
DYNATRACE_ONEAGENT = "name: dynatrace-oneagent\n"
DYNATRACE_ONEAGENT_WEBHOOK = "name: dynatrace-oneagent-webhook\n"
DYNATRACE_ONEAGENT_UNPRIVILEGED = "name: dynatrace-oneagent-unprivileged\n"

# Paths
PATH_OA_OP_CRDS = "./dynatrace-oneagent-operator/crds"
PATH_OA_OP_COMMON = "./dynatrace-oneagent-operator/templates/Common"
PATH_OA_OP_K8S = "./dynatrace-oneagent-operator/templates/Kubernetes"
PATH_OA_OP_OPENSHIFT = "./dynatrace-oneagent-operator/templates/Openshift"
PATH_OA_OP_GKE = "./dynatrace-oneagent-operator-google-marketplace/chart/dynatrace-oneagent-operator/templates"

##################################################################################################################

def open_oneagent_op_file(directory, dest_file):
    """ This method reads the file, which is given to it in combination with
        the specified directory.

    Parameters:
    -----------
    directory: the directory, which leads to the desired directory.

    dest_file: the file, in which the read data will be written.

    Returns
    -------
    data_string
        The string, which contains the complete yaml-file with its format.
    """

    with open(directory + "/" + dest_file, "r") as yamlfile:
        data_string = ""

        for line in yamlfile.readlines():

            # To let out the line for the platform - as it won't be needed in the gke marketplace
            if not "platformIsSet" in line:
                data_string += line

    return data_string

def write_into_dest_file(directory, source, dest_file, gke_flag):
    """ This method writes into the file, which is given to it in combination with
        the specified directory.

    Parameters:
    -----------
    directory: the directory, which specifies the current directory.

    source: the file, from which the data is read.

    dest_file: the file, in which the read data will be written.

    gke_flag: indicates, whether we are in the gke marketplace or not
    """

    # if the flag is set we know that we are in the gke folder, so we have to "build" the file step by step therefor we use the mode "a"
    with open(directory + "/" + dest_file, "a" if gke_flag else "w") as yamlfile:
        yamlfile.write(source)

def diff_oneagent_operator_with_gke(path, source, dest, gke_flag):
    """ This method writes into the file, which is given to it in combination with
        the specified directory.

    Parameters:
    -----------
    path: the directory, which specifies the current directory.

    source: the file, from which the data is read.

    dest: the file, in which the read data will be written.

    gke_flag: A flag, which indicates, whether we are working with the configmap file or not (as there are different tabspaces)

    Returns
    -------
    file_string
        The string, which holds the diffed file
    """

    with open(path + "/" + source, "r") as source_file:
        with open(path + "/" + dest, "r") as dest_file:
            list_source_file = source_file.readlines()
            list_dest_file = dest_file.readlines()
        
            index_diff = {}
            for line in list_source_file:
                # if there is a line which is not in the gke file we want to save it together with the index (linenumber)
                if line not in list_dest_file:
                    index_diff.update({list_source_file.index(line) + 1 : line})

            for i in range(len(list_source_file)):
                # if the current i is in the diff-index AND has go-templating we want to add that to the gke-file
                if i in index_diff and "{{" in list_source_file[i]:
                    # gke_flag indicates whether we have to add two additional tabspaces in order to keep the .yaml structure
                    if gke_flag:
                        list_dest_file.insert(i, "\t\t" + list_source_file[i])
                    else:
                        list_dest_file.insert(i, list_source_file[i])
            file_string = ""
            for line in list_dest_file:
                file_string += line

    return file_string

def get_files_out_of_configmap(path):
    """ This method gets the configmap.yaml and extracts the "subfiles" out of it.

    Parameters:
    -----------
    path: the directory, which specifies the current directory.

    Returns
    -------
    file_list
        A list, which holds the subfiles of the configmap.yaml
    """
    
    file_list = []  # list, which will hold all "subfiles" in the configmap
    index_list = [] # list, which will hold the indices where the files start
    with open(path, "r") as configmap:
        config_map = configmap.readlines()

        for index in range(len(config_map)):
            if ".yaml" in config_map[index]:
                # find the indices where a new kind starts
                index_list.append(index)
    
    # the start of configmap (until the start of the subfiles) has to stay the same so we put it in this list
    start_config_file = config_map[0 : index_list[0]]

    for i in range(len(index_list) - 1):
        # now slicing with the help of the found indices the file and saving the parts (which are the files) into a list of files
        file_list.append(config_map[index_list[i] : index_list[i + 1]])
    
    # appending the last slice from the last index until EOF (= last kind of the configmap)
    file_list.append(config_map[index_list[-1]:])
    return file_list, start_config_file

def build_file_string_from_list(file_list):
    """ This method generates a string out of a list with files.

    Parameters:
    -----------
    file_list: a list, which holds files.

    Returns
    -------
    str_list
        A list, which again holds the files, but not as a list type but as a string type.
    """

    str_list = []
    for files in file_list:
        str_file = ""
        for lines in files:
            str_file += lines
        str_list.append(str_file)
    
    return str_list

def find_name(file_list, name):
    """ This method gets a file in form of a list (it holds the lines of the file) and checks, whether 
        the searched name is in the list or not.

    Parameters:
    -----------
    file_list: A list, which holds the lines of a single file

    name: The item, which is searched.

    Returns
    -------
    Boolean
        True or false, whether the name is found.
    """

    for elem in file_list:
        if name in elem:
            return True
    
    return False

def copy_files(sourcepath, input_file, destpath, subfile):
    """ This method takes the input file, which was found, the respective paths and the matching subfile
        out of the configmap

    Parameters:
    -----------
    sourcepath: The path, where the input_file is located.

    input_file: The file out of the oneagent-operator

    destpath: The path, which leads to the gke marketplace

    subfile: The subfile out of the configmap, which matches with the input_file.
    """

    # Currently i am opening one file and saving the file as a string in the variable source.
    source = open_oneagent_op_file(sourcepath, input_file)
                
    # Here I take the created string with the file in it and write into a temp file.
    write_into_dest_file(destpath, source, "tmp-oneagent.yaml", False)

    with open(PATH_OA_OP_GKE + "/tmp-gke-sub.yaml", "w") as tmpfile:
        tmpfile.writelines(subfile)

    # here i take the temp and diff it with the configmap-subfile and return the diffed file as a string.
    file_string = diff_oneagent_operator_with_gke(destpath, "tmp-oneagent.yaml", "tmp-gke-sub.yaml", False)

    with open(PATH_OA_OP_GKE + "/tmp-gke.yaml", "a") as tmpfile:
        tmpfile.writelines(file_string)

    os.remove(PATH_OA_OP_GKE + "/tmp-oneagent.yaml")
    os.remove(PATH_OA_OP_GKE + "/tmp-gke-sub.yaml")

def simple_files():
    """ This method starts the process of copying the files which are not included 
        in the schema.yaml and the configmap.yaml
    """

    # Currently i am opening one file and saving the file as a string in the variable source. The input file is just for testing purposes
    source = open_oneagent_op_file(PATH_OA_OP_COMMON, "deployment-webhook.yaml")

    # Here I take the created string with the file in it and write into a temp file.
    write_into_dest_file(PATH_OA_OP_GKE, source, "tmp-oneagent.yaml", False)

    # here i take the temp and diff it with the gke-file and return the diffed file as a string.
    file_string = diff_oneagent_operator_with_gke(PATH_OA_OP_GKE, "tmp-oneagent.yaml", "deployment-webhook.yaml", False)

    # writing the generated file-string into the destination file.
    write_into_dest_file(PATH_OA_OP_GKE, file_string, "bla.yaml", False) # bla.yaml is only for testing purposes
    
    # removing the tmp file.
    os.remove(PATH_OA_OP_GKE + "/tmp-oneagent.yaml")

def configmap():
    """ This method starts the process of copying the files which are included
        in the configmap.yaml
    """
    config_map_files, start_of_file = get_files_out_of_configmap(PATH_OA_OP_GKE + "/configmap.yaml")
    
    with open(PATH_OA_OP_GKE + "/tmp-gke.yaml", "a") as tmpfile:
        tmpfile.writelines(start_of_file)
    
    # here the correct subfile will be choosen and given to the function copy_files with the respective filenames and paths
    for subfile in config_map_files:

        if KIND_PSP(subfile[0]):

            if find_name(subfile, "name: dynatrace-oneagent-operator\n"):
                copy_files(PATH_OA_OP_K8S, "podsecuritypolicy-operator.yaml", PATH_OA_OP_GKE, subfile)

            elif find_name(subfile, "name: dynatrace-oneagent\n"):
                copy_files(PATH_OA_OP_K8S, "podsecuritypolicy-oneagent.yaml", PATH_OA_OP_GKE, subfile)

            elif find_name(subfile, "name: dynatrace-oneagent-webhook\n"):
                copy_files(PATH_OA_OP_K8S, "podsecuritypolicy-webhook.yaml", PATH_OA_OP_GKE, subfile)

            elif find_name(subfile, "name: dynatrace-oneagent-unprivileged\n"):
                copy_files(PATH_OA_OP_K8S, "podsecuritypolicy-oneagent-unprivileged.yaml", PATH_OA_OP_GKE, subfile)

        elif KIND_CRD(subfile[0]):

            if KIND_APM(subfile[0]):
                copy_files(PATH_OA_OP_CRDS, "dynatrace.com_oneagentapms_crd.yaml", PATH_OA_OP_GKE, subfile)
            else:
                copy_files(PATH_OA_OP_CRDS, "dynatrace.com_oneagents_crd.yaml", PATH_OA_OP_GKE, subfile)

        elif KIND_ONEAGENT(subfile[0]):

            # copying these two files does not work correct. it appears that the diffing of the files is incorrect. The same goes for the mutatingwebhook file
            if KIND_APM(subfile[0]):
                copy_files(PATH_OA_OP_COMMON, "customresource-oneagentapm.yaml", PATH_OA_OP_GKE, subfile)
            else:
                copy_files(PATH_OA_OP_COMMON, "customresource-oneagent.yaml", PATH_OA_OP_GKE, subfile)

        else:
            copy_files(PATH_OA_OP_COMMON, "mutatingwebhookconfiguration.yaml", PATH_OA_OP_GKE, subfile)
        

if __name__ == "__main__":

    #simple_files()

    #configmap()
