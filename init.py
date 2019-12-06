#!/usr/bin/env python3

## \file init.py
#  \brief Initializes necessary dependencies for SU2 either using git or it
#         fetches zip files.
#  \author T. Albring
#  \version 6.2.0 "Falcon"
#
# The current SU2 release has been coordinated by the
# SU2 International Developers Society <www.su2devsociety.org>
# with selected contributions from the open-source community.
#
# Copyright 2012-2019, Francisco D. Palacios, Thomas D. Economon,
#                      Tim Albring, and the SU2 contributors.
#
# SU2 is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# SU2 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with SU2. If not, see <http://www.gnu.org/licenses/>.

import sys, os, subprocess, shutil, urllib.request, zipfile

def init_submodules(method = 'auto'):

  cur_dir = sys.path[0]

  # This information of the modules is used if projects was not cloned using git
  # The sha tag must be maintained manually to point to the correct commit
  sha_version_codi = '501dcf0305df147481630f20ce37c2e624fb351f'
  github_repo_codi = 'https://github.com/scicompkl/CoDiPack'
  sha_version_medi = 'a95a23ce7585905c3a731b28c1bb512028fc02bb'
  github_repo_medi = 'https://github.com/SciCompKL/MeDiPack'
  sha_version_amg = '0abd5b88a760736e6e5f2966c101a3d263ea030d'
  github_repo_amg = 'https://github.com/bmunguia/AMGIO'
  sha_version_meson = 'c904d3eefe2a01ca60027e2a5192e1f1c7ca5d9d'
  github_repo_meson = 'https://github.com/mesonbuild/meson'
  sha_version_ninja = 'e0bc2e5fd9036a31d507881e1383adde3672aaef'
  github_repo_ninja = 'https://github.com/ninja-build/ninja'

  medi_name = 'MeDiPack'
  codi_name = 'CoDiPack'
  amg_name = 'AMGIO'
  meson_name = 'meson'
  ninja_name= 'ninja'

  alt_name_medi =   cur_dir + '/externals/medi'
  alt_name_codi =   cur_dir + '/externals/codi'
  alt_name_amg = cur_dir + '/externals/AMGIO'
  alt_name_meson =  cur_dir + '/externals/meson'
  alt_name_ninja =  cur_dir + '/externals/ninja'

  if method == 'auto':
    is_git = is_git_directory(cur_dir)
  elif method == 'git':
    is_git = True
  elif method == 'url':
    is_git = False
  else:
    print('Invalid method')
    sys.exit(1)

  # If directory was cloned using git, use submodule feature 
  # to check and initialize submodules if necessary
  if is_git:
    submodule_status(alt_name_codi, sha_version_codi)
    submodule_status(alt_name_medi, sha_version_medi)
    submodule_status(alt_name_amg, sha_version_amg)
    submodule_status(alt_name_meson, sha_version_meson)
    submodule_status(alt_name_ninja, sha_version_ninja)
  # Otherwise download the zip file from git
  else:
    download_module(codi_name, alt_name_codi, github_repo_codi, sha_version_codi)
    download_module(medi_name, alt_name_medi, github_repo_medi, sha_version_medi)
    download_module(amg_name, alt_name_amg, github_repo_amg, sha_version_amg)
    download_module(meson_name, alt_name_meson, github_repo_meson, sha_version_meson)
    download_module(ninja_name, alt_name_ninja, github_repo_ninja, sha_version_ninja)

  # Some log and error files
  alt_name_amgint  = cur_dir + '/SU2_PY/SU2/amginria'
  log = open( 'preconf_inria.log', 'w' )
  err = open( 'preconf_inria.err', 'w' )

  # Setup AMG interface
  subprocess.call(['python setup.py','build_ext','--inplace'], cwd = alt_name_amgint, stdout = log, stderr = err, shell = True)

  # Setup pyamg
  try:
    import pyamg
  except ImportError:
    install_pyamg(log, err)

def is_git_directory(path = '.'):
  try:
     p = subprocess.call(["git", "branch"], stderr=subprocess.STDOUT, stdout=open(os.devnull, 'w'), cwd=path)
  except FileNotFoundError:
     print("git command not found. Using fall-back method to init submodules")
     return False
  except subprocess.CalledProcessError:
     print("Directory was not cloned using git. Using fall-back method to init submodules")
     return False
  return p == 0

def submodule_status(path, sha_commit):

  if not os.path.exists(path + '/' + sha_commit):

    # Check the status of the submodule
    status = subprocess.run(['git', 'submodule','status', path], stdout=subprocess.PIPE, check = True, cwd = sys.path[0]).stdout.decode('utf-8')

    # The first character of the output indicates the status of the submodule
    # '+' : The submodule does not match the SHA-1 currently in the index of the repository
    # '-' : The submodule is not initialized
    # ' ' : Correct version of submodule is initialized
    status_indicator = status[0][0]

    
    if status_indicator == '+':
      # Write a warning that the sha tags do not match
      sys.stderr.write('WARNING: the currently checked out submodule commit in '
                        + path + ' does not match the SHA-1 found in the index.\n')
      sys.stderr.write('Use \'git submodule update --init '+ path + '\' to reset the module if necessary.\n')
    elif status_indicator == '-':
      # Initialize the submodule if necessary 
      print('Initialize submodule ' + path + ' using git ... ')
      subprocess.run(['git', 'submodule', 'update', '--init', path], check = True, cwd = sys.path[0])

      # Check that the SHA tag stored in this file matches the one stored in the git index
      cur_sha_commit = status[1:].split(' ')[0]
      if (cur_sha_commit != sha_commit):
        print('SHA-1 tag stored in index does not match SHA tag stored in this script.')
        sys.exit(1)
  
  

def download_module(name, alt_name, git_repo, commit_sha):
  
  # ZipFile does not preserve file permissions. 
  # This is a workaround for that problem:
  # https://stackoverflow.com/questions/39296101/python-zipfile-removes-execute-permissions-from-binaries
  class MyZipFile(zipfile.ZipFile):
    def _extract_member(self, member, targetpath, pwd):
      if not isinstance(member, zipfile.ZipInfo):
        member = self.getinfo(member)

      targetpath = super()._extract_member(member, targetpath, pwd)

      attr = member.external_attr >> 16
      if attr != 0:
        os.chmod(targetpath, attr)
      return targetpath

  if not os.path.exists(alt_name + '/' + commit_sha):

    if os.path.exists(alt_name) and os.listdir(alt_name): 
      print('Directory ' + alt_name + ' is not empty')
      print('Maybe submodules are already cloned with git?')
      sys.exit(1) 
 
    else:
      print('Downloading ' + name + ' \'' + commit_sha + '\'')
    
      filename = commit_sha + '.zip'

      url = git_repo + '/archive/' + filename

      if not os.path.exists(sys.path[0] + '/' + filename):
        try:
          urllib.request.urlretrieve (url, commit_sha + '.zip')
        except RuntimeError as e:
          print(e)
          print('Download of module ' + name + ' failed.')
          print('Get archive at ' + url)
          print('and place it in the source code root folder')
          print('Run meson.py again')
          sys.exit()
   
      # Unzip file 
      zipf = MyZipFile(sys.path[0] + '/' + filename)
      zipf.extractall(sys.path[0] + '/externals')

      shutil.move(sys.path[0] + '/externals/' + name + '-' + commit_sha, alt_name)

      # Delete zip file
      os.remove(sys.path[0] + '/' + filename)

      # Create identifier
      f = open(alt_name + '/' + commit_sha, 'w')
      f.close()

def install_pyamg(log, err):
  # Install pyAMG
  try:
    import pyamg
  except ImportError:
    if sys.platform == 'linux' or sys.platform == 'linux2':
        print('Installing pyAMG for Linux.')
        import sysconfig
        if sysconfig.get_config_var('Py_UNICODE_SIZE') == 2:
            pyamg_whl = 'pyamg-1.0.0-cp27-cp27m-linux_x86_64.whl'
        else:
            pyamg_whl = 'pyamg-1.0.0-cp27-cp27mu-linux_x86_64.whl'

    elif sys.platform == 'darwin':
        print('Installing pyAMG for Mac.')
        pyamg_whl = 'pyamg-1.0.0-cp27-cp27m-macosx_10_9_x86_64.whl'
        
    try:
        subprocess.check_call('pip3 install --user externals/AMGIO/pyamg/Python3/' + pyamg_whl, stdout = log, stderr = err, shell = True)
        log.close()
        err.close()
    except:
        print('pyAMG installation failed')

  return True


   
if __name__ == '__main__':
  if sys.version_info[0] < 3:
    raise Exception("Script must be run using Python 3")
   
  # Set up the build environment, i.e. clone or download all submodules
  init_submodules(sys.argv[1])

  sys.exit(0)
