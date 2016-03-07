import json
from json.decoder import JSONDecodeError

from coalib.bearlib.abstractions.Lint import Lint
from coalib.bears.LocalBear import LocalBear
from coalib.results.Diff import Diff
from coalib.results.RESULT_SEVERITY import RESULT_SEVERITY
from coalib.misc.Shell import escape_path_argument
from coalib.results.Result import Result


class ESLintBear(LocalBear, Lint):
    executable = 'eslint'
    severity_map = {
        2: RESULT_SEVERITY.MAJOR,
        1: RESULT_SEVERITY.NORMAL,
        0: RESULT_SEVERITY.INFO
    }
    use_stdin = True

    def run(self, filename, file, eslint_config: str=""):
        '''
        Checks the code with eslint. This will run eslint over each of the files
        seperately.

        :param eslint_config: The location of the .eslintrc config file.
        '''
        self.arguments = '--no-ignore --no-color -f=json --stdin'
        if eslint_config:
            self.arguments += (" --config "
                               + escape_path_argument(eslint_config))

        return self.lint(filename, file)

    def _process_issues(self, output, filename):
        try:
            output = json.loads("".join(output))
        except JSONDecodeError:
            pass
        lines = [line for line in open(filename)]
        lines = "".join(lines)
        new_output = lines
        replacement_count = 0
        if len(output) == 1:
            for lint_result in output[0]['messages']:
                if lint_result['severity'] == 0:
                    continue
                if 'fix' in lint_result:
                    fix_structure = lint_result['fix']
                    starting_value, ending_value = fix_structure['range']
                    replacement_text = fix_structure['text']
                    if replacement_text != "":
                        len_of_replaced_text = ending_value - starting_value
                        replacement_count += len(replacement_text) - \
                            len_of_replaced_text
                    new_output = lines[:(starting_value)] +\
                        replacement_text + \
                        lines[(ending_value):]
                    diff = Diff.from_string_arrays(
                        lines.splitlines(True), new_output.splitlines(True))
                    print(new_output)

                    yield Result.from_values(
                        origin=self,
                        message=lint_result['message'],
                        file=filename,
                        diffs={filename: diff},
                        severity=self.severity_map[lint_result['severity']],
                        line=lint_result['line'])
                else:
                    yield Result.from_values(
                        origin=self,
                        message=lint_result['message'],
                        file=filename,
                        severity=self.severity_map[lint_result['severity']],
                        line=lint_result['line'])
        else:
            failure_message = """There is an issue with the bear.\
            Please file a bug at https://github.com/coala-analyzer/coala-bears
            """
            yield Result.from_values(
                origin=self,
                message=failure_message,
                file=filename)
