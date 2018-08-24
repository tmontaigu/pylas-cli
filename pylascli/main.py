import click
import pylas


@click.group()
def cli():
    pass


@cli.command()
@click.argument('input', type=click.File(mode='rb'))
@click.argument('output', type=click.Path())
@click.option('--point-format-id', default=None, type=int,
              help="Point format id to convert the file to. Allowed point formats: {}".format(
                  pylas.supported_point_formats()))
@click.option('--file-version', default=None, help="Version to convert to. Allowed versions: {}".format(
    pylas.supported_versions()
))
@click.option('--force', is_flag=True, help="Does not ask for confirmation when dimensions may be lost")
def convert(input, output, point_format_id, file_version, force):
    """
    Converts INPUT to a file with point_format_id and file_version
    Writes the result to OUTPUT

    If no file version or point_format_id is provided this will result in a copy
    """
    if point_format_id is not None and point_format_id not in pylas.supported_point_formats():
        click.echo(click.style('Point format {} is not supported'.format(point_format_id), fg='red'))
        raise click.Abort()

    if file_version is not None and file_version not in pylas.supported_versions():
        click.echo(click.style('LAS version {} is not supported'.format(file_version), fg='red'))
        raise click.Abort()

    las = pylas.read(input)
    if point_format_id is not None and not force:
        lost_dimensions = pylas.lost_dimensions(las.points_data.point_format.id, point_format_id)
        if lost_dimensions:
            click.echo("Converting  will lose: {}".format(
                lost_dimensions
            ))
            click.confirm("Continue ?", abort=True)

    try:
        las = pylas.convert(las, point_format_id=point_format_id, file_version=file_version)
    except pylas.errors.PylasError as e:
        click.echo(click.style("{}: {}".format(e.__class__.__name__, e), fg='red'))
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(str(e), fg='red'))
        raise click.Abort()
    else:
        las.write(output)


def echo_header(header):
    click.echo("File version : {}".format(header.version))
    click.echo("Point Format id {}".format(header.point_format_id))
    click.echo("Number of Points: {}".format(header.point_count))
    click.echo("Point size: {}".format(header.point_size))
    click.echo("Compressed: {}".format(header.are_points_compressed))
    click.echo("Creation date: {}".format(header.date))
    click.echo("Generating Software: {}".format(header.generating_software))
    click.echo("Number of VLRs: {}".format(header.number_of_vlr))
    if header.version >= '1.4':
        click.echo("Number of EVLRs: {}".format(header.number_of_evlr))
    click.echo("Scales: {}".format(header.scales))
    click.echo("Offsets: {}".format(header.offsets))
    click.echo("Mins: {}".format(header.mins))
    click.echo("Maxs: {}".format(header.maxs))


def echo_vlrs(fp):
    vlrs = fp.read_vlrs()
    for i, vlr in enumerate(vlrs, start=1):
        click.echo("VLR {} / {}".format(i, len(vlrs)))
        click.echo('\tVLR type: {}'.format(vlr.__class__.__name__))
        click.echo("\tUser id: {}".format(vlr.user_id))
        click.echo("\tRecord id: {}".format(vlr.record_id))
        click.echo("\tDescription: {}".format(vlr.description))
        click.echo("\tMore: {}".format(str(vlr)))


def echo_points(fp):
    point_records = fp.read().points_data
    click.echo("Available dimensions: {}".format(point_records.point_format.dimension_names))
    click.echo("Extra dimensions: {}".format(point_records.point_format.extra_dims))


@cli.command()
@click.argument("file", type=click.File(mode='rb'))
@click.option('--vlrs', default=False, is_flag=True, help="Read and print VLRs information")
@click.option('--points', default=False, is_flag=True, help='Read and print additional point information')
def info(file, vlrs, points):
    """
    Prints the file information to stdout.
    By default only information of the header are written
    """
    with pylas.open(file) as fp:
        echo_header(fp.header)

        if vlrs:
            click.echo(20 * "-")
            echo_vlrs(fp)

        if points:
            click.echo(20 * "-")
            echo_points(fp)


@cli.command(short_help='merge files together')
@click.argument("files", nargs=-1)
@click.argument('dst', nargs=1)
def merge(files, dst):
    """
    Merge the files listed in FILES and writes the result to DST
    """
    las_files = [pylas.read(file) for file in files]
    merged = pylas.merge(las_files)
    merged.write(dst)


if __name__ == '__main__':
    cli()
