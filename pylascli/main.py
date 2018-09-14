import os

import click
import fs
from progress.bar import IncrementalBar

import pylas


def openbin_file(url, mode='r'):
    basename, filename = os.path.split(url)
    with fs.open_fs(basename) as ffs:
        return ffs.openbin(filename, mode=mode)


@click.group()
def cli():
    pass


@cli.command()
@click.argument("input")
@click.argument("output")
@click.option(
    "--point-format-id",
    default=None,
    type=int,
    help="Point format id to convert the file to. Allowed point formats: {}".format(
        pylas.supported_point_formats()
    ),
)
@click.option(
    "--file-version",
    default=None,
    help="Version to convert to. Allowed versions: {}".format(
        pylas.supported_versions()
    ),
)
@click.option(
    "--force",
    is_flag=True,
    help="Does not ask for confirmation when dimensions may be lost",
)
def convert(input, output, point_format_id, file_version, force):
    """
    Converts INPUT to a file with point_format_id and file_version
    Writes the result to OUTPUT

    If no file version or point_format_id is provided this will result in a copy.

    Examples:

    1) Compress a file

        pylas convert stormwind.las stormwind.laz

    2) Convert file to point format 3

        pylas convert ironforge.las forgeiron.las --point-format-id 3
    """
    if (
            point_format_id is not None
            and point_format_id not in pylas.supported_point_formats()
    ):
        click.echo(
            click.style(
                "Point format {} is not supported".format(point_format_id), fg="red"
            )
        )
        raise click.Abort()

    if file_version is not None and file_version not in pylas.supported_versions():
        click.echo(
            click.style(
                "LAS version {} is not supported".format(file_version), fg="red"
            )
        )
        raise click.Abort()

    las = pylas.read(openbin_file(input))
    if point_format_id is not None and not force:
        lost_dimensions = pylas.lost_dimensions(
            las.points_data.point_format.id, point_format_id
        )
        if lost_dimensions:
            click.echo("Converting  will lose: {}".format(lost_dimensions))
            click.confirm("Continue ?", abort=True)

    try:
        las = pylas.convert(
            las, point_format_id=point_format_id, file_version=file_version
        )
    except pylas.errors.PylasError as e:
        click.echo(click.style("{}: {}".format(e.__class__.__name__, e), fg="red"))
        raise click.Abort()
    except Exception as e:
        click.echo(click.style(str(e), fg="red"))
        raise click.Abort()
    else:
        las.write(openbin_file(output, mode='w'), do_compress=output.endswith('.laz'))


def echo_header(header, extended=False):
    click.echo("File version : {}".format(header.version))
    click.echo("Point Format id {}".format(header.point_format_id))
    click.echo("Number of Points: {}".format(header.point_count))
    click.echo("Point size: {}".format(header.point_size))
    click.echo(
        "Number of points by return: {}".format(list(header.number_of_points_by_return))
    )
    click.echo("Compressed: {}".format(header.are_points_compressed))
    click.echo("Creation date: {}".format(header.date))
    click.echo("Generating Software: {}".format(header.generating_software))
    click.echo("Number of VLRs: {}".format(header.number_of_vlr))
    if header.version >= "1.4":
        click.echo("Number of EVLRs: {}".format(header.number_of_evlr))

    click.echo("")
    click.echo("Scales: {}".format(header.scales))
    click.echo("Offsets: {}".format(header.offsets))
    click.echo("Mins: {}".format(header.mins))
    click.echo("Maxs: {}".format(header.maxs))

    if extended:
        click.echo("")
        click.echo("Header size: {}".format(header.size))
        click.echo("Offset to points: {}".format(header.offset_to_point_data))


def echo_vlrs(fp):
    vlrs = fp.read_vlrs()
    for i, vlr in enumerate(vlrs, start=1):
        click.echo("VLR {} / {}".format(i, len(vlrs)))
        click.echo("\tVLR type: {}".format(vlr.__class__.__name__))
        click.echo("\tUser id: {}".format(vlr.user_id))
        click.echo("\tRecord id: {}".format(vlr.record_id))
        click.echo("\tDescription: {}".format(vlr.description))
        click.echo("\tMore: {}".format(str(vlr)))


def echo_points(fp):
    point_records = fp.read().points_data
    click.echo(
        "Available dimensions: {}".format(point_records.point_format.dimension_names)
    )
    click.echo("Extra dimensions: {}".format(point_records.point_format.extra_dims))

    for name in point_records.point_format.dimension_names:
        click.echo(name)
        array = point_records[name]
        click.echo("\tmin: {}".format(array.min()))
        click.echo("\tmax: {}".format(array.max()))


@cli.command()
@click.argument("file")
@click.option(
    "--extended",
    default=False,
    is_flag=True,
    help="Print more informations stored in the header",
)
@click.option(
    "--vlrs", default=False, is_flag=True, help="Read and print VLRs information"
)
@click.option(
    "--points",
    default=False,
    is_flag=True,
    help="Read and print additional point information",
)
def info(file, extended, vlrs, points):
    """
    Prints the file information to stdout.
    By default only information of the header are written
    """
    try:
        with pylas.open(openbin_file(file)) as fp:
            echo_header(fp.header, extended)

            if vlrs:
                click.echo(20 * "-")
                echo_vlrs(fp)

            if points:
                click.echo(20 * "-")
                echo_points(fp)
    except fs.errors.ResourceNotFound as e:
        click.echo(click.style("Error: {}".format(e), fg="red"))


@cli.command(short_help="merge files together")
@click.argument("files", nargs=-1)
@click.argument("dst", nargs=1)
def merge(files, dst):
    """
    Merge the files listed in FILES and writes the result to DST

    Examples:

    1) Merges all the files (*.las or *.laz) found in the folder 'a_folder' into a new
    file called merged.las

        pylas merge a_folder merged.las

    2) Merges 'ground.las' and 'vegetation.las' then writes the result into a new file 'scene.las'

        pylas merge ground.las vegetation.las scene.las

    """

    if len(files) == 0:
        raise click.BadArgumentUsage("Please provide both input files and destination file")

    if len(files) == 1:
        path = files[0]
        base, pattern = os.path.split(path)
        with fs.open_fs(base) as ffs:
            files = ["{}{}".format(base, match.path) for match in ffs.glob(pattern)]

    las_files = [pylas.read(openbin_file(f)) for f in IncrementalBar("Reading files").iter(files)]

    try:
        click.echo("Merging")
        merged = pylas.merge(las_files)
        click.echo("Writing")
        merged.write(openbin_file(dst, mode='w'), do_compress=dst.endswith('.laz'))
    except Exception as e:
        click.echo(click.style(str(e), fg="red"))
        raise click.Abort()


if __name__ == "__main__":
    cli()
