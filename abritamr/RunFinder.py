import pathlib, pandas, datetime, subprocess, os, logging,subprocess,collections, re
from abritamr.version import db
from abritamr.CustomLog import CustomFormatter


class RunFinder(object):
    """
    A class to run amrfinderplus
    """
    def __init__(self, args):
        
        self.logger =logging.getLogger(__name__) 
        self.logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(CustomFormatter())
        fh = logging.FileHandler('abritamr.log')
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(levelname)s:%(asctime)s] %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p') 
        fh.setFormatter(formatter)
        self.logger.addHandler(ch) 
        self.logger.addHandler(fh)
        self.db = db
        self.organism = args.organism
        self.input = args.input
        self.run_type = args.run_type
        self.jobs = args.jobs
        self.prefix = args.prefix
        self.identity = args.identity
        self.amrfinder_db = args.amrfinder_db

    def _batch_cmd(self):
        """
        generate cmd with parallel
        """
        org = f"--organism {self.organism}" if self.organism != '' else ''
        d = f" -d {self.amrfinder_db}" if self.amrfinder_db != '' else ''
        _id = f" --ident_min {self.identity} " if self.identity != '' else ''
        cmd = f"parallel -j {self.jobs} --colsep '\\t' 'mkdir -p {{1}} && amrfinder -n {{2}} -o {{1}}/amrfinder.out --plus {org} --threads 1{d}{_id}' :::: {self.input}"
        return cmd
    
    def _single_cmd(self):
        """
        generate a single amrfinder command
        """
        org = f"--organism {self.organism}" if self.organism != '' else ''
        d = f" -d {self.amrfinder_db}" if self.amrfinder_db else ''
        _id = f" --ident_min {self.identity} " if self.identity != '' else ''
        cmd = f"mkdir -p {self.prefix} && amrfinder -n {self.input} -o {self.prefix}/amrfinder.out --plus {org} --threads {self.jobs}{d}{_id}"
        return cmd
    
    def _check_amrfinder(self):
        """
        Check that amrfinder is installed and that a database is available.This does NOT enforce an exact DB version, only reports what is found.
        """
        self.logger.info(f"Checking AMRFinderPlus setup (expected DB ~ {self.db})")
        cmd = "amrfinder -V"
        p = subprocess.run(
            cmd,
            shell=True,
            encoding="utf-8",
            capture_output=True
        )

        if p.returncode != 0:
        self.logger.error(
            "AMRFinderPlus does not appear to be installed or runnable.\n"
            f"stderr:\n{p.stderr}"
            )
            return False

        output = p.stdout.strip()
        self.logger.info(f"Detected AMRFinderPlus:\n{output}")

        # Extract database version if present
        m = re.search(r'Database version\s+([0-9]{4}-[0-9]{2}-[0-9]{2}\.\d+)', output)
        if m:
            detected_db = m.group(1)
            self.logger.info(f"Detected AMRFinderPlus database version: {detected_db}")

            if self.db and self.db not in detected_db:
                self.logger.warning(
                    f"AMRFinderPlus DB version ({detected_db}) does not match "
                    f"expected version ({self.db}). Proceeding anyway."
                )
        else:
            self.logger.warning(
                "Could not detect AMRFinderPlus database version from `amrfinder -V` output."
            )

    return True


    def _generate_cmd(self):
        """
        Generate a command to run amrfinder
        """
        cmd = self._batch_cmd() if self.run_type == 'batch' else self._single_cmd()
        return cmd
        
    def _run_cmd(self, cmd):
        """
        Use subprocess to run the command for amrfinder
        """

        p = subprocess.run(cmd, shell = True, capture_output = True, encoding = "utf-8")
        if p.returncode == 0:
            self.logger.info(f"AMRfinder completed successfully. Will now move on to collation.")
            return True
        else:
            self.logger.critical(f"There appears to have been a problem with running amrfinder plus. The following erro has been reported : \n {p.stderr}")

    def _check_output_file(self, path):
        """
        check that amrfinderplus outputs are present
        """
        if not pathlib.Path(path).exists():
            self.logger.critical(f"The amrfinder output : {path} is missing. Something has gone wrong with AMRfinder plus. Please check all inputs and try again.")
            raise SystemExit
        else:
            return True

    def _check_outputs(self):
        """
        use inputs to check if files made
        """
        if self.run_type != 'batch':
            self._check_output_file(f"{self.prefix}/amrfinder.out")
        else:
            tab = pandas.read_csv(self.input, sep = '\t', header = None)
            for row in tab.iterrows():
                self._check_output_file(f"{row[1][0]}/amrfinder.out")
        return True

    def run(self):
        """
        run amrfinder
        """
        if self._check_amrfinder():
            self.logger.info(f"All check complete now running AMRFinder")
            
            
        else:
            self.logger.critical(f"Your amrfinder database version is NOT {self.db}. abriTAMR will still run but behaviour may not be as expected in terms of binnig genes into the appropriate drug classes.")
            # raise SystemExit
        cmd = self._generate_cmd()
        self.logger.info(f"You are running abritamr in {self.run_type} mode. Now executing : {cmd}")
        self._run_cmd(cmd)
        self._check_outputs()
        Data = collections.namedtuple('Data', ['run_type', 'input', 'prefix'])
        amr_data = Data(self.run_type, self.input, self.prefix)

        return amr_data
