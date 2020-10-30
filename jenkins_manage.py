#!/usr/bin/env python


import requests
import json
import yaml
# from config import Config
# from load_roles import (Pattern, Connector, Project_items, Sid_roles, 
        # Product_global_permission, Item_global_permission, Env_global_permission,
        # Product_project_permission, Item_project_permission, Env_project_permission, Environments)

class Jenkins_manage:
    def __init__(self, url, username, password):
        self.url = url
        if self.url[-1] != '/':
            self.url = self.url + '/'
        self.str_url = self.url + 'role-strategy/strategy'
        
        self.username = username
        self.password = password
        self.session = requests.session()
        self.session.auth=(self.username, self.password)
        self.crumb = self.get_crumb()

        self.data = self.load_yaml()
        common = self.data.get('common')
        self.Connector = common.get('connector')
        self.Pattern = common.get('pattern')
        self.Environments = common.get('env')

    def load_yaml(self):
        with open('jenkins_roles.yaml', 'r', encoding='utf-8') as f:
            return yaml.load(f.read())

    def check_result(self, resp):
        if resp.status_code == requests.codes.ok:
            pass
            # print("Request success!")
        else:
            print(f"Request failed!")
            print(resp.text)
            print(resp.url)
            exit(1)

    def get_crumb(self):
        crumb_url = self.url + '/crumbIssuer/api/json'
        resp = self.session.get(crumb_url)
        data = json.loads(resp.text)
        return {data.get("crumbRequestField"):data.get("crumb")}


    def get_role(self, type, roleName):
        '''
        @type: globalRoles or projectRoles
        @roleName: str
        '''
        get_role_url = self.str_url + '/getRole'
        params = {
            'type' : type,
            'roleName' : roleName
        }
        resp = self.session.get(get_role_url, params=params)
        if resp.status_code == requests.codes.ok:
            return resp.text
        else:
            print(resp.text)
            return None

    def add_role(self, type, roleName, permissionIds, overwrite=True, pattern=None):
        '''
        * @param type          (globalRoles, projectRoles)
        * @param roleName      Name of role
        * @param permissionIds Comma separated list of IDs for given roleName
        * @param overwrite     Overwrite existing role
        * @param pattern       Role pattern
        * @throws IOException  In case saving changes fails
        '''
        add_role_url = self.str_url + '/addRole'
        data = {
            'type': type,
            'roleName': roleName,
            'permissionIds': permissionIds,
            'overwrite': overwrite,
            'pattern': pattern if pattern is not None else f"{roleName}{self.Connector}{self.Pattern}"
        }
        data.update(self.crumb)
        resp = self.session.post(add_role_url, data=data)
        self.check_result(resp)

    def del_role(self, type, roleNames):
        '''
        * @param type      (globalRoles, projectRoles, slaveRoles)
        * @param roleNames comma separated list of roles to remove from type
        '''
        del_role_url = self.str_url + '/removeRoles'
        data = {
            "type": type,
            "roleNames": roleNames
        }
        data.update(self.crumb)
        resp = self.session.post(del_role_url, data=data)
        self.check_result(resp)
        
    def assign_role(self, type, roleName, sid):
        '''
        * @param type     (globalRoles, projectRoles, slaveRoles)
        * @param roleName name of role (single, no list)
        * @param sid      user ID (single, no list)
        '''
        assign_role_url = self.str_url + '/assignRole'
        data = {
            "type": type,
            "roleName": roleName,
            "sid": sid
        }
        data.update(self.crumb)
        resp = self.session.post(assign_role_url, data=data)
        self.check_result(resp)

    def init_all(self):

        func = lambda x: ','.join(x) if isinstance(x, list) else x
        # 创建全局角色
        role_global = self.data.get('roles').get('global')
        for role in role_global.keys():
            print(f"role: {role}")
            self.add_role('globalRoles', role, func(role_global.get(role)))

        # 创建项目角色
        role_project = self.data.get('roles').get('project')
        for project in self.data.keys():
            print(f"project: {project}")
            if project in ('roles', 'common'):
                continue
            
            # 分配系统 leader 权限
            self.add_role('projectRoles', project, func(role_project.get('leader')))
            proj_obj = self.data.get(project)
            items = proj_obj.get('items')
            for item in items:

                # 分配项目 item 权限
                print(f"project: {project}, item: {item}")
                self.add_role('projectRoles', project + self.Connector + item, func(role_project.get('item')))
                for env in self.Environments:
                    self.add_role('projectRoles', project + self.Connector + item + self.Connector + env, func(role_project.get('env')))

            # 分配用户权限
            sids = proj_obj.get('sids')
            if sids:
                for sid, sid_role in sids.items():
                    print(f"sid: {sid}")
                    for permiss in sid_role.get('global'):
                        self.assign_role('globalRoles', permiss, sid)
                    for permiss in sid_role.get('project'):
                        self.assign_role('projectRoles', permiss, sid)


if __name__ == "__main__":
    # config = Config.dev
    config = {
        'url': 'http://127.0.0.1:30080/',
        'username': 'admin',
        'password': 'admin123',
    }
    jm = Jenkins_manage(config['url'], config['username'], config['password'])
    jm.init_all()