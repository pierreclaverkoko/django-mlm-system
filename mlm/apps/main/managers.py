from django.db import models
from django.utils import timezone
from django.utils.translation import gettext as _

from .exceptions import OperationAmountError, OperationClientError


class MLMTransactionManager(models.Manager):
    """

    """

    def make_operation(self, client, amount, debit_credit, initiated_by=None):
        if client is None:
            raise OperationClientError(_("Client must be given."))

        if not client.is_active or not client.user.is_active:
            raise OperationClientError(_("Client must be active."))

        if amount is None or amount <= 0:
            raise OperationAmountError(_("Amount must be given."))

        if debit_credit == self.model.DEBIT:
            balance_after = client.available_amount - amount
            if amount > client.available_amount:
                raise OperationAmountError(
                    _("Credit limit reached: Insufficient funds.")
                )

        elif debit_credit == self.model.CREDIT:
            balance_after = client.available_amount + amount
        else:
            raise OperationAmountError(_("Amount movement must be given."))

        reference = self.model.get_next_ref_no()

        tr = self.model(
            client=client,
            amount=amount,
            initiated_by=initiated_by,
            debit_credit=debit_credit,
            balance_after=balance_after,
            reference_number=reference,
        )

        tr.reference_line = (
            self.model.objects.filter(
                created_at__year=timezone.now().year, reference_number=reference
            ).aggregate(models.Max("reference_number"))["reference_number__max"]
            or 1
        )

        tr.save()

        if debit_credit == self.model.DEBIT:
            client.available_amount -= amount
        elif debit_credit == self.model.CREDIT:
            client.available_amount += amount
        client.save()

        return tr

    def make_credit(self, client, amount, initiated_by=None):
        """ """
        return self.make_operation(
            client, amount, debit_credit=self.model.CREDIT, initiated_by=initiated_by
        )

    def make_debit(self, client, amount, initiated_by=None):
        """ """
        return self.make_operation(
            client, amount, debit_credit=self.model.DEBIT, initiated_by=initiated_by
        )


class MLMClientManager(models.Manager):
    def get_main(self, user):
        return self.model.objects.filter(user=user).first()  # is_main=True, user=user)
