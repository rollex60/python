import argparse, os, hashlib, logging, shutil, schedule, signal, sys
from datetime import datetime


# Execute only once - Arguments
def clean_arg(arg):
    if arg[-1] == '/':
        arg = arg[0:-1]
    return arg
parser = argparse.ArgumentParser()
parser.add_argument('-s', type = str, help = 'Source folder path', required = True)
parser.add_argument('-r', type = str, help = 'Replica folder path', required = True)
parser.add_argument('-i', type = int, help = 'Interval between synchronization [seconds]', required = True)
parser.add_argument('-l', type = str, help = 'Log file path', required = True)
args = parser.parse_args()
source, replica, interval, log = clean_arg(args.s), clean_arg(args.r), args.i, clean_arg(args.l)

# Execute only once - Create log file with first execution date as name
log_file = f'{log}/log-{datetime.now().strftime("%Y-%m-%d")}'
if not os.path.isfile(log_file):
    try:
        os.system(f'touch {log_file}')
    except Exception as e:
        print(e)

def update_log(type, incident_type, rel_path):
    '''
    Updates the log file and logs into console
    '''
    incident = { # Setting up some fancy colors
        'creation' : '\033[32m',
        'deletion' : '\033[91m',
        'warning' : '\033[33m',
        'replacement' : '\033[36m',
        'end' : '\033[0m'
    }
    print(f'{incident[incident_type]}{type} {incident_type}: {rel_path}{incident["end"]}') # Shows only relative path on terminal...
    try:
        logging.basicConfig(filename=log_file, level=logging.INFO)
        if incident_type == 'warning':
            logging.error(f' {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} > {type} {incident_type}: {replica}{rel_path}') # ...but logs the full path
        else:
            logging.info(f' {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} > {type} {incident_type}: {replica}{rel_path}')
    except Exception as e:
        print(f'Error writing to log file: {e}')

def list_files_dirs(route):
    '''
    Scans the "route" path and returns a list
    with all the directories in the path
    Strategy: From root to leaves.
    '''
    files_list = []
    dirs_list = []
    for root, dirs, files in os.walk(route, topdown=True):
        for name in files:
            files_list.append(os.path.join(root, name).replace(route, '')) # Sanitizing the output while keeping the structure
        for name in dirs:
            dirs_list.append(os.path.join(root, name).replace(route, ''))
    return dirs_list, files_list

def update_dirs(list_source, list_replica):
    '''
    Looks for directories in both directions.
    parameters:
    list_source: List with all the directories in the source path
    list_replica: List with all the directories in the replica path
    '''
    # Remove old unexisting directories from replica
    for dir in list_replica:
        if dir not in list_source:
            try:
                shutil.rmtree(replica+dir)
                update_log('Directory', 'deletion', dir)
            except Exception as e:
                print(e)
                update_log('Directory', 'warning', dir)
    # Create new directories
    for dir in list_source:
        if dir not in list_replica:
            try:
                os.mkdir(replica+dir)
                update_log('Directory', 'creation', dir)
            except Exception as e:
                print(e)
                update_log('Directory', 'warning', dir)

def update_files(list_source, list_replica):
    '''
    Looks for files in both directions.
    parameters:
    list_source: List with all the files in the source path
    list_replica: List with all the files in the replica path
    '''   
    # Remove old unexisting files from replica
    for file in list_replica:
        if file not in list_source:
            try:
                os.remove(replica+file)
                update_log('File', 'deletion', file)
            except Exception as e:
                print(e)
                update_log('File', 'warning', file)

    #Check for new/updated files
    for file in list_source:
        # 1. Copy new files
        if file not in list_replica: 
            try:
                shutil.copy2(source+file, replica+file)
                update_log('File', 'creation', file)
            except Exception as e:
                print(e)
                update_log('File', 'warning', file)
        # 2. Check for updated files
        else: 
            if os.path.getsize(source+file) == os.path.getsize(replica+file): # Same size => Check the MD5 hash
                md5_source = hashlib.md5(open(source+file, 'rb').read()).hexdigest()
                md5_replica = hashlib.md5(open(replica+file, 'rb').read()).hexdigest()
                if (md5_source != md5_replica): # Different hash => Replace
                    try:
                        os.remove(replica+file)
                        shutil.copy2(source+file, replica+file)
                        update_log('File', 'replacement', file)
                    except Exception as e:
                        print(e)
                        update_log('File', 'warning', file)
            else: # Different size => Just replace
                try:
                    os.remove(replica+file)
                    shutil.copy2(source+file, replica+file)
                    update_log('File', 'replacement', file)
                except Exception as e:
                    print(e)
                    update_log('File', 'warning', file)

signal.signal(signal.SIGINT, lambda x, y: sys.exit(0)) # Prevents traceback on Ctrl-c
print(f'Synchronizer input values:\n-Source: {source}\n-Replica: {replica}\n-Interval: {interval}\n-Log: {log}\n\n')

def synchronizer():
    print(f'Synchronization started at {datetime.now().replace(microsecond=0)} (ctrl+c to exit)...')
    source_dirs, source_files = list_files_dirs(source)
    replica_dirs, replica_files = list_files_dirs(replica)
    update_dirs(source_dirs, replica_dirs)
    update_files(source_files, replica_files)
    print('Synchronization finished.')

synchronizer() # First run
schedule.every(interval).seconds.do(synchronizer)
while True:
    schedule.run_pending()
