# 
# Authenticate against OpenStack Keystone
#

import hashlib
import json
import os
import sys
import syslog
import traceback
import urllib2

import yaml
import memcache

CLOUD_CONFIG_YAML = '/etc/openstack/clouds.yaml'

def pam_sm_authenticate(pamh, flags, argv):

    # Read an OpenStack cloud-config YAML file for the Keystone API endpoint
    with open(CLOUD_CONFIG_YAML, 'r') as fp:
        try:
            cloud_cfg = yaml.safe_load(fp)
            keystone_api = cloud_cfg['clouds'][argv[1]]['auth']['auth_url']
        except:
            syslog.syslog(syslog.LOG_AUTH | syslog.LOG_INFO,
                "PAM-Keystone: Unable to read Keystone endpoint from %s" %
                CLOUD_CONFIG_YAML)
            return pamh.PAM_AUTH_ERR

    try:
        pamh.user
        pamh.authtok
        if pamh.authtok == None:
            passmsg = pamh.Message(pamh.PAM_PROMPT_ECHO_OFF, "Keystone password: ")
            rsp = pamh.conversation(passmsg)
            pamh.authtok = rsp.resp
        try:
            mu = hashlib.sha1()
            mu.update(pamh.user)
            mp = hashlib.sha1()
            mp.update(pamh.authtok)
            mc = memcache.Client(['127.0.0.1:11211'])
            v = mc.get("%s-%s" % (mu.hexdigest(),mp.hexdigest()))
            if v != None:
                return pamh.PAM_SUCCESS

            val = {
                "auth": {
                    "passwordCredentials": {
                        "password": pamh.authtok,
                        "username": pamh.user
                    }
                }
            }
            keystone_url = keystone_api + '/v2.0/tokens'
            req = urllib2.Request(keystone_url)
            req.add_header('Content-Type', 'application/json')
            try:
                syslog.syslog(syslog.LOG_AUTH | syslog.LOG_DEBUG,
                    "PAM-Keystone: User %s authenticating with Keystone %s"
                    % (pamh.user, keystone_url))

                response = urllib2.urlopen(req, json.dumps(val))

                if (response.getcode() == 200):
                    mc.set("%s-%s" % (mu.hexdigest(),mp.hexdigest()),"true", 900)
                    syslog.syslog(syslog.LOG_AUTH | syslog.LOG_INFO,
                        "PAM-Keystone: User %s authenticated" % pamh.user)
                    return pamh.PAM_SUCCESS
            except Exception as E:
                # Don't want this error, its the 401
                syslog.syslog(syslog.LOG_AUTH | syslog.LOG_DEBUG,
                    "PAM-Keystone: Auth failure for user %s endpoint %s: %s:%s" %
                    (pamh.user, keystone_url, type(E), E))
                pass
        except:
            syslog.syslog(syslog.LOG_AUTH | syslog.LOG_NOTICE,
                "PAM-Keystone: Fail for %s (%s)" % (pamh.user, traceback.format_exc()))
            pass
    except:
        syslog.syslog(syslog.LOG_AUTH | syslog.LOG_ERR,
            "PAM-Keystone: Unhandled exception %s " % traceback.format_exc())
    return pamh.PAM_AUTH_ERR

def pam_sm_setcred(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_acct_mgmt(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_open_session(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_close_session(pamh, flags, argv):
  return pamh.PAM_SUCCESS

def pam_sm_chauthtok(pamh, flags, argv):
  return pamh.PAM_SUCCESS
