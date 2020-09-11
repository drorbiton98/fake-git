# upload 176

import collections
import datetime
import filecmp
import os
import random
import shutil
import sys

import graphviz


class dircmp(filecmp.dircmp):
    # credit for Philippe Ombredanne, 2nd comment:
    # https://stackoverflow.com/questions/4187564/recursively-compare-two-directories-to-ensure-they-have-the-same-files-and-subdi
    def phase3(self):
        fcomp = filecmp.cmpfiles(self.left, self.right, self.common_files, shallow=False)
        self.same_files, self.diff_files, self.funny_files = fcomp


class WitNotFoundError(Exception):
    pass


class IdNotExistError(Exception):
    pass


class FilesNotSavedError(Exception):
    pass


def get_head_id(current_dir):
    ref = os.path.join(current_dir, '.wit', 'references.txt')

    if os.path.exists(ref):
        with open(ref, 'r') as search:
            parent_id = search.readline().split("=")[1].replace('\n', '')
            return parent_id.replace(' ', '')
    return None


def get_master_id(current_dir):
    ref = os.path.join(current_dir, '.wit', 'references.txt')

    if os.path.exists(ref):
        with open(ref, 'r') as search:
            parent_id = search.readlines()[1].split("=")
            return parent_id[1].replace(' ', '')
    return None


def get_image_parent(image_txt):
    if os.path.exists(image_txt):
        with open(image_txt, 'r') as search:
            parent_id = search.readline().split("=")[1].replace('\n', '')
            return parent_id.replace(' ', '')
    return None


def check_if_branch(branch):
    ref = os.path.join(os.getcwd(), '.wit', 'references.txt')

    if os.path.exists(ref):
        with open(ref, 'r') as search:
            lines = search.read().split('\n')
            for line in lines[1:]:
                line = line.split('=')
                if branch == line[0]:
                    return True
    return False


def get_branch_id(branch):
    ref = os.path.join(os.getcwd(), '.wit', 'references.txt')

    if os.path.exists(ref):
        with open(ref, 'r') as search:
            lines = search.read().split('\n')
            for line in lines:
                line = line.split('=')
                if branch in line:
                    return line[1].replace(' ', '')
    return None


def doc_add(file_name, file_base_path, final_path):
    current_dir = os.path.join(os.getcwd(), '.wit', 'staging_area')
    doc_file = os.path.join(current_dir, 'doc.txt')
    half_path = os.path.join(*final_path)
    with open(doc_file, 'a') as doc:
        doc.write(f"{file_name}|{file_base_path}|{half_path}\n")


def diff_files_from_common_dirs(common_dirs, main_file, secondary_file):
    diff_files = []

    for subdir in common_dirs:
        compared = dircmp(os.path.join(secondary_file, subdir[1:]), os.path.join(main_file, subdir[1:]))
        diff_files += compared.diff_files
    return diff_files


def files_from_diff_dirs(diff_dirs, live_file):
    diff_files = []
    for directory in diff_dirs:
        full_dir = os.path.join(live_file, directory[1:])
        for file in os.listdir(full_dir):
            if os.path.isfile(os.path.join(full_dir, file)):
                diff_files.append(file)
    return diff_files


def changes_to_be_commited():
    current_dir = os.getcwd()
    last_id = get_head_id(current_dir)

    if not last_id:
        return None

    live_file = os.path.join(current_dir, '.wit', 'staging_area')
    last_file = os.path.join(current_dir, '.wit', 'images', last_id)

    last_dirs = {x[0].replace(last_file, '') for x in os.walk(last_file)}
    live_dirs = {x[0].replace(live_file, '') for x in os.walk(live_file)}

    common_dirs = live_dirs.intersection(last_dirs)
    diff_dirs = live_dirs.difference(last_dirs)

    return diff_files_from_common_dirs(common_dirs, live_file, last_file) + files_from_diff_dirs(diff_dirs, live_file)


def changes_not_staged_for_commit():
    current_dir = os.path.join(os.getcwd(), '.wit', 'staging_area')
    doc_path = os.path.join(current_dir, 'doc.txt')

    changed_files = []

    with open(doc_path, 'r') as open_doc:
        files = open_doc.read().split()
    splitted_files = [file.split('|') for file in files]

    file_names = [file[0] for file in splitted_files]
    original_paths = [file[1] for file in splitted_files]
    dir_trees = [file[2] for file in splitted_files]

    for path in original_paths:
        if os.path.isfile(path):
            if not filecmp.cmp(path, os.path.join(current_dir, dir_trees[original_paths.index(path)])):
                changed_files.append(file_names[original_paths.index(path)])
        else:
            base_path = path.replace(dir_trees[original_paths.index(path)], '')[:-1]

            dirs_of_backup = {x[0].replace(current_dir, '') for x in os.walk(current_dir)}
            dirs_of_original = {x[0].replace(base_path, '') for x in os.walk(base_path)}

            common_dirs = dirs_of_original.intersection(dirs_of_backup)

            files_after_comparison = diff_files_from_common_dirs(common_dirs, base_path, current_dir)
            if files_after_comparison:
                changed_files += files_after_comparison
    return set(changed_files)


def untracked_files():
    current_dir = os.path.join(os.getcwd(), '.wit', 'staging_area')
    doc_path = os.path.join(current_dir, 'doc.txt')

    with open(doc_path, 'r') as open_doc:
        files = open_doc.read().split()
    splitted_files = [file.split('|') for file in files]

    original_paths = [file[1] for file in splitted_files]
    dir_trees = [file[2] for file in splitted_files]

    untracked = []
    stage_files = [x[2] for x in os.walk(current_dir)]
    
    for path in original_paths:
        base_path = path.replace(dir_trees[original_paths.index(path)], '')[:-1]

        files_in_base = [x[2] for x in os.walk(base_path)]

        for sublist in files_in_base:
            for file in sublist:
                if file not in stage_files:
                    untracked.append(file)
    return untracked


def init():
    current_dir = os.getcwd()
    wit_folder = os.path.join(current_dir, '.wit')
    if not os.path.exists(wit_folder):
        os.mkdir(wit_folder)
    folders = ('images', 'staging_area')
    for folder in folders:
        path = os.path.join(wit_folder, folder)
        if not os.path.exists(path):
            os.mkdir(path)
    with open(os.path.join(wit_folder, 'activated.txt'), 'w') as activate:
        activate.write('master')


def add(file_path):    
    file_base_path = os.path.abspath(file_path)
    stripped_path, file_name = os.path.split(file_base_path)
    final_path = collections.deque([])

    if os.path.isfile(file_base_path):
        final_path.append(file_name)
    else:
        stripped_path = file_base_path

    while '.wit' not in os.listdir(stripped_path):
        stripped_path, obj = os.path.split(stripped_path)
        if obj:
            final_path.appendleft(obj)
        else:
            raise WitNotFoundError("Sorry, The directory tree chosen doesn't contain a .wit file.")

    current_dir = os.getcwd()
    if '.wit' not in os.listdir(current_dir):
        init()

    current_dir = os.path.join(current_dir, '.wit', 'staging_area')

    if len(final_path) > 0:
        for item in final_path:
            current_dir = os.path.join(current_dir, item)
            if not os.path.exists(current_dir):
                os.mkdir(current_dir)

    current_dir = os.path.join(file_name)

    if os.path.isdir(file_base_path):
        shutil.copytree(file_base_path, current_dir)
    else:
        shutil.copy(file_base_path, current_dir)
    doc_add(file_name, file_base_path, final_path)


def commit(message):
    running_dir = os.getcwd()
    if '.wit' not in os.listdir(running_dir):
        init()

    letters = (chr(letter) for letter in range(ord('a'), ord('z') + 1))
    nums = (str(num) for num in range(0, 10))
    notes = list(letters) + list(nums)
    commit_id = ''.join(random.choices(notes, k=40))

    current_dir = os.path.join(running_dir, '.wit')
    images = current_dir + "\\images"
    while commit_id in os.listdir(images):
        commit_id = ''.join(random.choices(notes, k=40))
    
    commit_path = f"{images}\\{commit_id}"
    with open(commit_path + '.txt', 'w') as txt_file:
        now = datetime.datetime.now()
        txt_file.write(f"parent={get_head_id(running_dir)}\n")
        txt_file.write(f"date={now.strftime('%A')} {now.strftime('%b')} {now.hour}:{now.minute}:{now.second} {now.year} {now.astimezone().strftime('%z')}\n")
        txt_file.write(f"message={message}\n\n")

    shutil.copytree(current_dir + "\\staging_area", commit_path)
    ref_path = os.path.join(running_dir, '.wit', 'references.txt')
    
    active_path = os.path.join(current_dir, 'activated.txt')
    with open(active_path, 'r') as activated:
        active_branch = activated.read()
    
    if not os.path.exists(ref_path) or (get_head_id(running_dir) == get_branch_id(active_branch) and active_branch == 'master'):
        head_line = f"HEAD={commit_id}\nmaster={commit_id}\n{active_branch}={commit_id}"
        with open(ref_path, 'w') as ref:
            ref.write(head_line)
    else:
        head_line = f"HEAD={commit_id}\n"
        with open(ref_path, 'r') as ref:
            lines = ref.readlines()
            lines[0] = head_line
            if active_branch != 'None':
                for line in lines:
                    if line.split('=')[0] == active_branch:
                        ind = lines.index(line)
                        lines[ind].split('=')[1] = lines[0].split('=')[1]
        with open(ref_path, 'w') as ref:
            ref.writelines(lines)


def status():
    current_dir = os.getcwd()
    last_save = get_head_id(current_dir)

    current_status = f"""last id = {last_save}
    changes to be committed: {changes_to_be_commited()}
    changes not staged for commit: {changes_not_staged_for_commit()}
    untracked files: {untracked_files()}
    """
    return current_status


def checkout(input_id):
    current_dir = os.getcwd()
    is_branch = check_if_branch(input_id)
    branch_id = input_id

    if is_branch:
        branch_id = get_branch_id(input_id)
    
    commit_id = os.path.join(current_dir, '.wit', 'images', branch_id)
    if not os.path.exists(commit_id):
        raise IdNotExistError("ID folder chosen does not exist, please check your input")

    elif changes_to_be_commited() or changes_not_staged_for_commit():
        raise FilesNotSavedError("Some files that supposed to be saved aren't, please run the COMMIT action.")

    if is_branch:
        with open(os.path.join(current_dir, '.wit', 'activated.txt'), 'w') as active:
            active.write(input_id)
    else:
        with open(os.path.join(current_dir, '.wit', 'activated.txt'), 'w') as active:
            active.write('None')

    source_dirs = {x[0] for x in os.walk(commit_id)}

    for src_directory in source_dirs:
        dst_directory = src_directory.replace(commit_id, current_dir)
        if not os.path.exists(dst_directory):
            os.makedirs(dst_directory)
        for file in os.listdir(src_directory):
            path_to_file = os.path.join(commit_id, src_directory, file)
            if os.path.isfile(path_to_file):
                src_file = os.path.join(src_directory, file)
                dst_file = os.path.join(dst_directory, file)
                shutil.copyfile(src_file, dst_file)
    dst_staging = os.path.join(current_dir, '.wit', 'staging_area')
    shutil.copytree(commit_id, dst_staging, dirs_exist_ok=True)

    ref_path = os.path.join(current_dir, '.wit', 'references.txt')
    head_line = f"HEAD= {os.path.basename(commit_id)}\n"
    with open(ref_path, 'r') as ref:
        lines = ref.readlines()
    lines[0] = head_line
    with open(ref_path, 'w') as ref:
        ref.writelines(lines)


def graph():
    current_dir = os.getcwd()
    images = os.path.join(current_dir, '.wit', 'images')

    start = get_head_id(current_dir)
    if start is None:
        return "No ID was found"

    graph = graphviz.Graph('screenshots', filename='screenshots', format='png')
    
    screenshot = os.path.join(images, start) + '.txt'
    count = 0
    graph.node(str(count), start)
    end = get_image_parent(screenshot)

    while end:
        count += 1
        graph.node(str(count), end)
        screenshot = os.path.join(images, end) + '.txt'
        end = get_image_parent(screenshot)

    graph.edges([str(num) + str(num + 1) for num in range(count)])
    graph.view()


def branch(name):
    current_dir = os.getcwd()
    ref = os.path.join(current_dir, '.wit', 'references.txt')
    with open(ref, 'a') as ref_file:
        ref_file.write(f"\n{name}={get_head_id(current_dir)}")


def check_wit():
    current_dir = os.getcwd()
    while '.wit' not in os.listdir(current_dir):
        current_dir, head = os.path.split(current_dir)
        if not head:
            return False
    return True


if check_wit():    
    if sys.argv[1] == 'init':
        init()
    elif sys.argv[1] == 'add':
        add(sys.argv[2])
    elif sys.argv[1] == 'commit':
        commit(sys.argv[2])
    elif sys.argv[1] == 'status':
        print(status())
    elif sys.argv[1] == 'checkout':
        checkout(sys.argv[2])
    elif sys.argv[1] == 'graph':
        graph()
    elif sys.argv[1] == 'branch':
        branch(sys.argv[2])
    else:
        print('sorry, did not recognize your command')
else:
    print("sorry, no '.wit' folder found in the dir tree")