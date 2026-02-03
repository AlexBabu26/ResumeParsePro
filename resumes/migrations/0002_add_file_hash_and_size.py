# Generated migration to add file_hash and file_size fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('resumes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='resumedocument',
            name='file_hash',
            field=models.CharField(blank=True, db_index=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='resumedocument',
            name='file_size',
            field=models.BigIntegerField(default=0),
        ),
        migrations.AddIndex(
            model_name='resumedocument',
            index=models.Index(fields=['uploaded_by', 'file_hash'], name='resumes_res_uploade_idx'),
        ),
    ]

