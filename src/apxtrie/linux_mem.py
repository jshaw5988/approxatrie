import os
import resource

_proc_status = f'/proc/{os.getpid()}/status'
_scale = {'kB': 1024.0, 'mB': 1024.0*1024.0,
          'KB': 1024.0, 'MB': 1024.0*1024.0}

# pylint: disable=invalid-name
def _VmB(VmKey):
    ''' given a VmKey string, returns a number of bytes. '''
    # get pseudo file  /proc/<pid>/status
    try:
        with open(_proc_status, encoding="utf-8") as status_file:
            status = status_file.read()
    except OSError:
        return 0.0  # non-Linux?
    # get VmKey line e.g. 'VmRSS:  9999  kB\n ...'
    idx = status.index(VmKey)
    v = status[idx:].split(None, 3)  # split on runs of whitespace
    if len(v) < 3:
        return 0.0  # invalid format?
    # # convert Vm value to bytes
    return float(v[1]) * _scale[v[2]]

# pylint: disable=invalid-name
def _VmMb(VmKey):
    xbytes = _VmB(VmKey)
    # convert Vm value to megabytes
    return xbytes / (1024.0 * 1024.0)

def memory(since=0.0):
    ''' Return virtual memory usage in bytes. '''
    return _VmB('VmSize:') - since

def resident(since=0.0):
    ''' Return resident memory usage in bytes. '''
    return _VmB('VmRSS:') - since

def stacksize(since=0.0):
    ''' Return stack size in bytes. '''
    return _VmB('VmStk:') - since

def memory_mb(since=0.0):
    ''' Return virtual memory usage in bytes. '''
    return _VmMb('VmSize:') - since

def resident_mb(since=0.0):
    ''' Return resident memory usage in bytes. '''
    return _VmMb('VmRSS:') - since

def stacksize_mb(since=0.0):
    ''' Return stack size in bytes. '''
    return _VmMb('VmStk:') - since

def peak_resident_memory():
    usage = resource.getrusage(resource.RUSAGE_SELF)
    for name, desc in [
            ('ru_utime', 'User time'),
            ('ru_stime', 'System time'),
            ('ru_maxrss', 'Max. Resident Set Size'),
            ('ru_ixrss', 'Shared Memory Size'),
            ('ru_idrss', 'Unshared Memory Size'),
            ('ru_isrss', 'Stack Size'),
            ('ru_inblock', 'Block inputs'),
            ('ru_oublock', 'Block outputs'),
    ]:
        print(f'{desc:<25} ({name:<10}) = {getattr(usage, name)}')
        # return usage[4]
    return usage.ru_maxrss / 1000
