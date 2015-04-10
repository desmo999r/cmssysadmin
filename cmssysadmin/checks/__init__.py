import logging
import rpm

logger = logging.getLogger(__name__)

def checkRunningKernel(expectedKernel):
    logger.debug("About to check running kernel")
    with open("/proc/sys/kernel/osrelease") as f:
        runningKernel = f.readline().strip()
    if runningKernel == expectedKernel:
        logger.info("Current running kernel is the expected one: %s", expectedKernel)
        return True
    else:
        logger.error("Wrong running kernel: %s, the expected one is: %s", runningKernel, expectedKernel)
        return False

def checkPackage(name, version=False):
    logger.debug("About to check package %s", name)
    ts = rpm.TransactionSet()
    mi = ts.dbMatch('name', name)
    for h in mi:
        if version and "{0}-{1}".format(h['version'], h['release']) == version:
            logger.info("Installed version (%s) of %s is correct", version, name)
            return True
        elif version:
            logger.error("Package %s is installed but the version is wrong (installed=%s-%s, expected=%s)", name, h['version'], h['release'], version)
            return False
        else:
            logger.info("Package %s is installed", name)
            return True
    logger.error("Package %s is NOT installed", name)
    return False
