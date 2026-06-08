from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('configdetails', '0014_dispenserkeyadmapping'),
    ]

    operations = [
        migrations.CreateModel(
            name='MQTTTokenLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('raw_payload', models.TextField(help_text='Original MQTT payload string')),
                ('customer_id', models.CharField(max_length=100)),
                ('mac_address', models.CharField(blank=True, max_length=100)),
                ('message_type_char', models.CharField(blank=True, help_text='Raw char from payload[3] (A/B/C/D/E/CLR)', max_length=5)),
                ('message_type', models.CharField(
                    choices=[
                        ('NORMAL',   'Normal Token'),
                        ('TRANSFER', 'Transfer'),
                        ('SKIP',     'Skip'),
                        ('SPECIAL',  'Special Message'),
                        ('VIP',      'VIP / Emergency'),
                        ('CLEAR',    'Clear Tokens'),
                        ('UNKNOWN',  'Unknown'),
                    ],
                    default='UNKNOWN',
                    max_length=20,
                )),
                ('keypad_serial', models.CharField(blank=True, max_length=50)),
                ('keypad_index', models.CharField(blank=True, max_length=10)),
                ('token_number', models.CharField(blank=True, max_length=20)),
                ('button_string_id', models.CharField(
                    blank=True,
                    help_text='For type C: payload[22], selects the button string to display',
                    max_length=10,
                )),
                ('counter_name', models.CharField(blank=True, max_length=150)),
                ('received_at', models.DateTimeField()),
                ('displayed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(
                    choices=[
                        ('received',  'Received'),
                        ('displayed', 'Displayed'),
                        ('announced', 'Announced'),
                    ],
                    default='received',
                    max_length=20,
                )),
                ('announcement_status', models.CharField(
                    choices=[
                        ('pending',   'Pending'),
                        ('completed', 'Completed'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('is_valid', models.BooleanField(default=True)),
                ('is_duplicate', models.BooleanField(default=False)),
                ('is_uploaded', models.BooleanField(
                    default=False,
                    help_text='Set True once this log has been confirmed uploaded; '
                              'records older than 2 days with this flag are auto-deleted.',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('counter', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='mqtt_logs',
                    to='configdetails.counterconfig',
                )),
                ('keypad', models.ForeignKey(
                    blank=True, null=True,
                    limit_choices_to={'device_type': 'KEYPAD'},
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='mqtt_logs',
                    to='configdetails.device',
                )),
            ],
            options={
                'verbose_name': 'MQTT Token Log',
                'verbose_name_plural': 'MQTT Token Logs',
                'ordering': ['-received_at'],
            },
        ),
        migrations.AddIndex(
            model_name='mqtttokenlog',
            index=models.Index(fields=['customer_id', '-received_at'], name='mqtt_cust_recv_idx'),
        ),
        migrations.AddIndex(
            model_name='mqtttokenlog',
            index=models.Index(fields=['keypad_serial', '-received_at'], name='mqtt_kp_recv_idx'),
        ),
        migrations.AddIndex(
            model_name='mqtttokenlog',
            index=models.Index(fields=['is_valid', 'is_duplicate'], name='mqtt_valid_dup_idx'),
        ),
    ]
