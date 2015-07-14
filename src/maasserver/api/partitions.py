# Copyright 2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""API handlers: `Partition`."""

from __future__ import (
    absolute_import,
    print_function,
    unicode_literals,
    )

str = None

__metaclass__ = type

from django.shortcuts import get_object_or_404
from maasserver.api.support import (
    admin_method,
    operation,
    OperationsHandler,
)
from maasserver.enum import NODE_PERMISSION
from maasserver.exceptions import (
    MAASAPIBadRequest,
    MAASAPINotFound,
    MAASAPIValidationError,
)
from maasserver.forms import (
    FormatPartitionForm,
    MountPartitionForm,
)
from maasserver.models import (
    BlockDevice,
    Node,
    Partition,
    PartitionTable,
)
from maasserver.utils.converters import machine_readable_bytes
from piston.utils import rc


DISPLAYED_PARTITION_FIELDS = (
    'id',
    'uuid',
    'size',
    'start_offset',
    'bootable',
    ('filesystem', (
        'fstype',
        'label',
        'uuid',
        'mount_point',
    )),
)


class PartitionTableHandler(OperationsHandler):
    """Manage partitions on a partition table on a block device on a node."""
    api_doc_section_name = "Partitions"
    create = replace = update = delete = None
    model = PartitionTable
    fields = DISPLAYED_PARTITION_FIELDS

    def read(self, request, system_id, device_id):
        """List all partitions on the partition table of a block device
        belonging to a node.

        :param system_id: The node to query.
        :param device_id: The block device.

        Returns 404 if the node or the block device or partition table are not
        found.
        """
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.VIEW)
        device = get_object_or_404(BlockDevice, id=device_id)
        if device.node != node:
            raise MAASAPINotFound()
        partition_table = device.partitiontable_set.get()
        return partition_table.partitions.all()

    @admin_method
    @operation(idempotent=False)
    def add_partition(self, request, system_id, device_id):
        """Add a partition

        :param system_id: The node to query.
        :param device_id: The block device.
        """
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.ADMIN)
        device = get_object_or_404(BlockDevice, id=device_id)
        if device.node != node:
            raise MAASAPINotFound()

        partition_table = device.partitiontable_set.get()
        offset = machine_readable_bytes(request.POST.get('offset', None))
        size = machine_readable_bytes(request.POST.get('size', None))

        partition = partition_table.add_partition(
            start_offset=offset, size=size)
        return partition


class PartitionHandler(OperationsHandler):
    """Manage single partition on a block device on a node."""
    api_doc_section_name = "Partitions"
    create = replace = update = None
    model = Partition
    fields = DISPLAYED_PARTITION_FIELDS

    def read(self, request, system_id, device_id, partition_id):
        """Read partition on block device on node.

        :param system_id: The node to query.
        :param device_id: The block device.
        :param partition_id: The partition.

        Returns 404 if the node or the partition table or the block device or
        the partition are not found.

        """
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.VIEW)
        device = get_object_or_404(BlockDevice, id=device_id)
        partition_table = device.partitiontable_set.get()
        if device.node != node:
            raise MAASAPINotFound()
        partition = partition_table.partitions.get(id=partition_id)
        return partition

    def delete(self, request, system_id, device_id, partition_id):
        """Delete a partition

        :param system_id: The node to query.
        :param device_id: The block device.
        :param partition_id: The partition.
        """
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.ADMIN)
        device = get_object_or_404(BlockDevice, id=device_id)
        if device.node != node:
            raise MAASAPINotFound()
        partition_table = device.partitiontable_set.get()
        partition = partition_table.partitions.get(id=partition_id)
        partition.delete()
        return rc.DELETED

    @operation(idempotent=False)
    def format(self, request, system_id, device_id, partition_id):
        """Format a partition.

        :param system_id: The node to query.
        :param device_id: The block device.
        :param partition_id: The partition.

        Returns 403 when the user doesn't have the ability to format the
            partition.
        Returns 404 if the node, block device or partition is not found.
        """
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.EDIT)
        device = get_object_or_404(BlockDevice, id=device_id)
        if device.node != node:
            raise MAASAPINotFound()
        partition_table = get_object_or_404(
            PartitionTable, block_device=device)
        partition = get_object_or_404(
            Partition, partition_table=partition_table, id=partition_id)
        data = request.data
        form = FormatPartitionForm(partition, data=data)
        if form.is_valid():
            form.save()
        else:
            raise MAASAPIValidationError(form.errors)
        return partition

    @operation(idempotent=False)
    def unformat(self, request, system_id, device_id, partition_id):
        """Unformat a partition."""
        node = Node.nodes.get_node_or_404(
            system_id, request.user, NODE_PERMISSION.EDIT)
        device = get_object_or_404(BlockDevice, id=device_id)
        if device.node != node:
            raise MAASAPINotFound()
        partition_table = get_object_or_404(
            PartitionTable, block_device=device)
        partition = get_object_or_404(
            Partition, partition_table=partition_table, id=partition_id)
        filesystem = partition.filesystem
        if filesystem is None:
            raise MAASAPIBadRequest("Partition is not formatted.")
        if filesystem.mount_point:
            raise MAASAPIBadRequest(
                "Filesystem is mounted and cannot be unformatted. Unmount the "
                "filesystem before unformatting the partition.")
        if filesystem.filesystem_group is not None:
            raise MAASAPIBadRequest(
                "Filesystem is part of a filesystem group, and cannot be "
                "unformatted. Remove partition from filesystem group "
                "before unformatting the partition.")
        partition.remove_filesystem()
        return partition

    @operation(idempotent=False)
    def mount(self, request, system_id, device_id, partition_id):
        """Mount the filesystem on partition.

        :param mount_point: Path on the filesystem to mount.

        Returns 403 when the user doesn't have the ability to mount the
            partition.
        Returns 404 if the node, block device or partition is not found.
        """
        device = BlockDevice.objects.get_block_device_or_404(
            system_id, device_id, request.user, NODE_PERMISSION.EDIT)
        partition_table = get_object_or_404(PartitionTable,
                                            block_device=device)
        partition = get_object_or_404(Partition,
                                      partition_table=partition_table,
                                      id=partition_id)
        form = MountPartitionForm(partition, data=request.data)
        if form.is_valid():
            return form.save()
        else:
            raise MAASAPIValidationError(form.errors)

    @operation(idempotent=False)
    def unmount(self, request, system_id, device_id, partition_id):
        """Unmount the filesystem on partition.

        Returns 400 if the partition is not formatted or not currently
            mounted.
        Returns 403 when the user doesn't have the ability to unmount the
            partition.
        Returns 404 if the node, block device os partition is not found.
        """
        device = BlockDevice.objects.get_block_device_or_404(
            system_id, device_id, request.user, NODE_PERMISSION.EDIT)
        partition_table = get_object_or_404(PartitionTable,
                                            block_device=device)
        partition = get_object_or_404(Partition,
                                      partition_table=partition_table,
                                      id=partition_id)
        filesystem = partition.filesystem
        if filesystem is None:
            raise MAASAPIBadRequest("Partition is not formatted.")
        if not filesystem.mount_point:
            raise MAASAPIBadRequest("Filesystem is already unmounted.")
        filesystem.mount_point = None
        filesystem.save()
        return partition
