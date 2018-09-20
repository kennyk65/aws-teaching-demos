# Do nothing.  Better to put stop activities in "before_install".
# This script always lags behind the rest of the scripts anyway; 
# the revision (containing this script) is not downloaded until AFTER this point, 
# so the script that runs is always from the PREVIOUS revision (ugh).  
# Since that is needlessly irritating, it is just simpler to do everything in "before_install".
