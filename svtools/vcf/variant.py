from svtools.vcf.genotype import Genotype
import sys

class Variant(object):
    '''
    Class for storing information stored in a VCF line
    '''
    def __init__(self, var_list, vcf):
        '''
        Initialize values.

        If fixed_genotypes is True then a string corresponding to the
        genotype portion of the line is cached for printing later.
        '''
        self.chrom = var_list[0]
        self.pos = int(var_list[1])
        self.var_id = var_list[2]
        self.ref = var_list[3]
        self.alt = var_list[4]
        self.qual = var_list[5]
        self.filter = var_list[6]
        self.sample_list = vcf.sample_list
        self.info_list = vcf.info_list
        self.info = dict()
        self.format_list = vcf.format_list
        self.format_set = {i.id for i in vcf.format_list}
        self.active_formats = set()
        self.active_format_list = list()
        self.gts = None

        # fill in empty sample genotypes
        if len(var_list) < 8:
            sys.stderr.write('\nError: VCF file must have at least 8 columns\n')
            exit(1)

        # make a genotype for each sample at variant
        self.format_string = var_list[8]
        self.active_formats = { i for i in self.format_string.split(':') }
        self.update_active_format_list()
        self.gts_string = '\t'.join(var_list[9:])

        self.info = dict()
        i_split = [a.split('=') for a in var_list[7].split(';')] # temp list of split info column
        for i in i_split:
            if len(i) == 1:
                i.append(True)
            self.info[i[0]] = i[1]

    def _parse_genotypes(self, format_field_tags, genotype_array):
        '''
        Parse the genotype strings
        '''
        gts = dict()
        for index, sample_string in enumerate(genotype_array):
            sample_name = self.sample_list[index]
            try:
                sample_field = sample_string.split(':')
                # sample_name HAS to match the same order.
                gts[sample_name] = Genotype(self, sample_field[0])
                # import the existing fmt fields
                gts[sample_name].set_formats(format_field_tags, sample_field)
            except IndexError:
                gts[sample_name] = Genotype(self, './.')
        return gts

    def update_active_format_list(self):
        '''
        Update the set of this lines 'active' formats.
        This tracks which of the listed formats are actually being used.
        '''
        new_list = list()
        for format in self.format_list:
            if format.id in self.active_formats:
                new_list.append(format.id)
        self.active_format_list = new_list

    def set_info(self, field, value):
        '''
        Set value of the specified field in the INFO section.
        The INFO field must exist already.
        '''
        if field in [i.id for i in self.info_list]:
            self.info[field] = value
        else:
            sys.stderr.write('\nError: invalid INFO field, \"' + field + '\"\n')
            exit(1)

    def get_info(self, field):
        '''
        Get a value for the given INFO field
        '''
        return self.info[field]

    def get_info_string(self):
        '''
        Construct the INFO string for printing. Order is matched to the header.
        '''
        i_list = list()
        for info_field in self.info_list:
            if info_field.id in self.info.keys():
                if info_field.type == 'Flag':
                    if self.info[info_field.id]:
                        i_list.append(info_field.id)
                else:
                    i_list.append('%s=%s' % (info_field.id, self.info[info_field.id]))
        return ';'.join(i_list)

    def get_format_string(self):
        '''
        Construct the FORMAT field containing the names of the fields in the Genotype columns
        '''
        if self.format_string is not None:
            return self.format_string
        else:
            f_list = list()
            for f in self.format_list:
                if f.id in self.active_formats:
                    f_list.append(f.id)
            return ':'.join(f_list)

    def get_gt_string(self, use_cached_gt_string=False):
        '''
        Construct the genotype string.
        '''
        if self.gts:
            if use_cached_gt_string:
                return self.gts_string
            else:
                return '\t'.join(self.genotype(s).get_gt_string() for s in self.sample_list)
        else:
            return self.gts_string

    def genotype(self, sample_name):
        '''
        Return the Genotype object for the requested sample
        '''
        if self.gts is None:
            self.gts = self._parse_genotypes(self.format_string.split(':'), self.gts_string.split('\t'))
            self.format_string = None
        try:
            return self.gts[sample_name]
        except KeyError as e:
            sys.stderr.write('\nError: invalid sample name, \"' + sample_name + '\"\n')
            sys.exit(1)

    def get_var_string(self, use_cached_gt_string=False):
        '''
        Return the String representation for this line
        '''
        fields = [
                self.chrom,
                self.pos,
                self.var_id,
                self.ref,
                self.alt,
                self.qual,
                self.filter,
                self.get_info_string()
                ]

        if not (len(self.active_formats) == 0 and self.format_string is None):
            gts_string = self.get_gt_string(use_cached_gt_string)
            if gts_string is None:
                sys.stderr.write("Unable to construct or retrieve genotype string\n")
                sys.exit(1)
            else:
                fields += [
                        self.get_format_string(),
                        gts_string
                    ]
        return '\t'.join(map(str, fields))
