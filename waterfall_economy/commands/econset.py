"""
Economy settings command.
"""

from ..util.embeds import SettingChangedEmbed, ErrorEmbed, AdminEmbed

from redbot.core import Config, commands, app_commands, bank
from redbot.core.commands.converter import TimedeltaConverter
from redbot.core.utils.chat_formatting import humanize_number
from redbot.core.commands.requires import PrivilegeLevel

from datetime import datetime, timezone, timedelta

import discord
import calendar
import yaml
import io
import pprint
import datetime as dt

from random import randint, randrange


class EconomySettingsCommand(commands.Cog):
  """
  All the economy configuration subcommands
  """

  def __init__(self, bot):
    """Initialise the cog."""
    # super().__init__()
    self.bot = bot
    self.config = None  # make the config field, but it gets overridden so it's fine

  @commands.group(name="econset")
  @commands.admin()
  async def command_econset(self, ctx):
    """Set Waterfall Economy settings"""
    pass

  @command_econset.group(name="steal")
  async def command_econset_steal(self, ctx):
    """Set steal settings"""
    pass

  @command_econset_steal.command(name="showsettings")
  async def command_econset_steal_showsettings(self, ctx):
    """Show the steal settings"""
    steal_rate = await self.config.STEAL_SUCCESS_RATE()
    steal_immunity = await self.config.STEAL_IMMUNITY()
    steal_cooldown = await self.config.STEAL_COOLDOWN()
    steal_min = await self.config.STEAL_MIN()
    steal_max = await self.config.STEAL_MAX()

    await ctx.send(embed=discord.Embed(
      description=f"Steal Success Rate: {steal_rate}%\nSteal Immunity Duration: {steal_immunity} seconds\nSteal Cooldown: {steal_cooldown} seconds\nMin Steal Amount: {humanize_number(steal_min)}\nMax Steal Amount: {humanize_number(steal_max)}",
      title="Steal Settings",
      colour=discord.Colour.gold()
    ))

  @command_econset_steal.command(name="rate")
  async def command_econset_steal_rate(self, ctx, rate: int):
    """Set the success rate for the steal command"""
    if rate < 0 or rate > 100:
      await ctx.send(embed=ErrorEmbed("The success rate must be between 0 and 100!"))
      return

    await self.config.STEAL_SUCCESS_RATE.set(rate)
    await ctx.send(embed=SettingChangedEmbed("Steal Success Rate", str(rate)))

  @command_econset_steal.command(name="cooldown")
  async def command_econset_steal_cooldown(self, ctx, cooldown: TimedeltaConverter):
    """Set the cooldown for the steal command"""
    await self.config.STEAL_COOLDOWN.set(cooldown.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Steal Cooldown", str(cooldown)))

  @command_econset_steal.command(name="min")
  async def command_econset_steal_min(self, ctx, min_amount: int):
    """Set the minimum amount that can be stolen"""
    if min_amount < 1:
      await ctx.send(embed=ErrorEmbed("The minimum amount that can be stolen must be at least 1!"))
      return
    await self.config.STEAL_MIN.set(min_amount)
    await ctx.send(embed=SettingChangedEmbed("Min Steal Amount", humanize_number(min_amount)))

  @command_econset_steal.command(name="max")
  async def command_econset_steal_max(self, ctx, max_amount: int):
    """Set the maximum amount that can be stolen"""
    if max_amount < 1:
      await ctx.send(embed=ErrorEmbed("The maximum amount that can be stolen must be at least 1!"))
      return
    await self.config.STEAL_MAX.set(max_amount)
    await ctx.send(embed=SettingChangedEmbed("Max Steal Amount", humanize_number(max_amount)))

  @command_econset_steal.command(name="immunity")
  async def command_econset_steal_immunity(self, ctx, immunity: TimedeltaConverter):
    """Set the immunity duration for the steal command"""
    await self.config.STEAL_IMMUNITY.set(immunity.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Steal Immunity Duration", str(immunity)))

  @command_econset_steal.group(name="clear")
  async def command_econset_steal_clear(self, ctx):
    """Clear steal cooldowns and immunities"""
    pass

  @command_econset_steal_clear.group(name="cooldown")
  async def command_econset_steal_clear_cooldown(self, ctx):
    """Clear steal cooldown."""
    pass

  @command_econset_steal_clear_cooldown.command(name="user")
  async def command_econset_steal_clear_cooldown_user(self, ctx, target: discord.Member):
    """Clear the cooldown for a user's steal command"""
    await self.config.member(target).steal_cooldown.set(0)
    await ctx.send(embed=AdminEmbed(
      message="{target.mention}'s steal cooldown has been reset!",
      author=ctx.author,
      title="Steal Cooldown Reset"
    ))

  @command_econset_steal_clear_cooldown.command(name="all")
  async def command_econset_steal_clear_cooldown_all(self, ctx):
    """Clear everyone's steal cooldown"""
    i = 0
    for member in ctx.guild.members:
      await self.config.member(member).steal_cooldown.set(0)
      i += 1

    await ctx.send(embed=AdminEmbed(
      message=f"Steal cooldown has been reset for **{i}** users!",
      author=ctx.author,
      title="Steal Cooldowns Reset"
    ))

  @command_econset_steal_clear.group(name="immunity")
  async def command_econset_steal_clear_immunity(self, ctx):
    """Clear steal immunity."""
    pass

  @command_econset_steal_clear_immunity.command(name="user")
  async def command_econset_steal_clear_immunity_user(self, ctx, target: discord.Member):
    """Clear the immunity for a user's steal command"""
    await self.config.member(target).steal_immunity.set(0)
    await ctx.send(embed=AdminEmbed(
      message=f"{target.mention}'s steal immunity has been reset!",
      author=ctx.author,
      title="Steal Immunity Reset"
    ))

  @command_econset_steal_clear_immunity.command(name="all")
  async def command_econset_steal_clear_immunity_all(self, ctx):
    """Clear everyone's steal immunity"""
    i = 0
    for member in ctx.guild.members:
      await self.config.member(member).steal_immunity.set(0)
      i += 1

    await ctx.send(embed=AdminEmbed(
      message=f"Steal immunity has been reset for **{i}** users!",
      author=ctx.author,
      title="Steal Immunities Reset"
    ))

  @command_econset.group(name="work", aliases=["job"])
  async def command_econset_work(self, ctx):
    """Set work settings"""
    pass

  @command_econset_work.command(name="showsettings")
  async def command_econset_work_showsettings(self, ctx):
    """Show the work settings"""
    job_cooldown = await self.config.JOB_COOLDOWN()
    job_apply_cooldown = await self.config.JOB_APPLY_COOLDOWN()
    job_count = len(await self.config.JOBS())

    await ctx.send(embed=AdminEmbed(
      message=f"Work Cooldown: {job_cooldown} seconds\nJob Application Cooldown: {job_apply_cooldown} seconds\nJobs: {job_count}",
      author=ctx.author,
      title="Work Settings"
    ))

  @command_econset_work.command(name="cooldown")
  async def command_econset_work_cooldown(self, ctx, cooldown: TimedeltaConverter):
    """Set the cooldown for the work command"""
    await self.config.JOB_COOLDOWN.set(cooldown.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Work Cooldown", str(cooldown)))

  @command_econset_work.command(name="applycooldown")
  async def command_econset_work_applycooldown(self, ctx, cooldown: TimedeltaConverter):
    """Set the cooldown for applying for a job"""
    await self.config.JOB_APPLY_COOLDOWN.set(cooldown.total_seconds())
    await ctx.send(embed=SettingChangedEmbed("Job Application Cooldown", str(cooldown)))

  @command_econset_work.group(name="clearcooldown")
  async def command_econset_work_clearcooldown(self, ctx):
    """Clear work cooldown."""
    pass

  @command_econset_work_clearcooldown.command(name="user")
  async def command_econset_work_clearcooldown_user(self, ctx, target: discord.Member, cd_type: str = "work"):
    """Clear the cooldown for a user's work command"""
    if cd_type == "work":
      await self.config.member(target).job_last_worked.set(0)
    elif cd_type == "apply":
      await self.config.member(target).job_last_quit.set(0)
    elif cd_type == "all":
      await self.config.member(target).job_last_worked.set(0)
      await self.config.member(target).job_last_quit.set(0)
    else:
      await ctx.send(embed=ErrorEmbed("Invalid cooldown type!"))
      return

    await ctx.send(embed=AdminEmbed(
      message=f"{target.mention}'s {'work' if cd_type != 'apply' else 'job application'} {'cooldowns have' if cd_type == 'all' else 'cooldown has'} has been reset!",
      author=ctx.author,
      title="Work Cooldown Reset",
      colour=discord.Colour.gold()
    ))

  @command_econset_work_clearcooldown.command(name="all")
  async def command_econset_work_clearcooldown_all(self, ctx):
    """Clear everyone's work cooldown"""
    i = 0
    for member in ctx.guild.members:
      await self.config.member(member).job_last_worked.set(0)
      i += 1

    await ctx.send(embed=AdminEmbed(
      message=f"Work cooldown has been reset for **{i}** users!",
      author=ctx.author,
      title="Work Cooldowns Reset"
    ))

  @command_econset_work.group(name="jobs")
  async def command_econset_work_jobs(self, ctx):
    """Modify jobs"""
    pass

  @command_econset_work_jobs.command(name="add")
  async def command_econset_work_jobs_add(self, ctx, job_id: str, name: str, description: str, emoji: str, min_times_worked: int = 0):
    """Add a job"""
    jobs = await self.config.JOBS()
    jobs[job_id] = {
      "name": name,
      "description": description,
      "emoji": emoji,
      "min_times_worked": min_times_worked,
      "tiers": []
    }
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Added", name))

  @command_econset_work_jobs.command(name="remove")
  async def command_econset_work_jobs_remove(self, ctx, job_id: str):
    """Remove a job"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    del jobs[job_id]
    await self.config.JOBS.set(jobs)
    # Remove the job from all users who had it
    for user in ctx.guild.members:
      if await self.config.member(user).job() == job_id:
        await self.config.member(user).job.set(None)
        await self.config.member(user).job_tier.set(0)
        await self.config.member(user).job_times_worked.set(0)

    await ctx.send(embed=SettingChangedEmbed("Job Removed", job_id))

  @command_econset_work_jobs.group(name="edit")
  async def command_econset_work_jobs_edit(self, ctx, job_id: str, name: str = None, description: str = None, emoji: str = None, min_times_worked: int = None):
    """Edit jobs"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    job = jobs[job_id]
    if name:
      job["name"] = name
    if description:
      job["description"] = description
    if emoji:
      job["emoji"] = emoji
    if min_times_worked is not None:
      job["min_times_worked"] = min_times_worked
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Edited", job["name"]))

  @command_econset_work_jobs.group(name="tiers")
  async def command_econset_work_jobs_tiers(self, ctx):
    """Modify job tiers"""
    pass

  @command_econset_work_jobs_tiers.command(name="add")
  async def command_econset_work_jobs_tiers_add(self, ctx, job_id: str, name: str, rate: int, min_hours: int, max_hours: int):
    """Add a job tier"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    job = jobs[job_id]
    job["tiers"].append({
      "name": name,
      "rate": rate,
      "min_hours": min_hours,
      "max_hours": max_hours,
      "times_worked": 0
    })
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Tier Added", name))

  @command_econset_work_jobs_tiers.command(name="remove")
  async def command_econset_work_jobs_tiers_remove(self, ctx, job_id: str, tier: int):
    """Remove a job tier"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    job = jobs[job_id]
    if tier >= len(job["tiers"]):
      await ctx.send(embed=ErrorEmbed("That tier does not exist!"))
      return
    name = job["tiers"][tier]["name"]
    del job["tiers"][tier]
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Tier Removed", name))

  @command_econset_work_jobs_tiers.command(name="edit")
  async def command_econset_work_jobs_tiers_edit(self, ctx, job_id: str, tier: int, name: str = None, rate: int = None, min_hours: int = None, max_hours: int = None):
    """Edit a job tier"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    job = jobs[job_id]
    if tier >= len(job["tiers"]):
      await ctx.send(embed=ErrorEmbed("That tier does not exist!"))
      return
    job = job["tiers"][tier]
    if name:
      job["name"] = name
    if rate:
      job["rate"] = rate
    if min_hours:
      job["min_hours"] = min_hours
    if max_hours:
      job["max_hours"] = max_hours
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Tier Edited", job["name"]))

  @command_econset_work_jobs_tiers.command(name="reorder", aliases=["reorganise"])
  async def command_econset_work_jobs_tiers_reorder(self, ctx, job_id: str, *indices: int):
    """Reorder job tiers"""
    jobs = await self.config.JOBS()
    if job_id not in jobs:
      await ctx.send(embed=ErrorEmbed("That job does not exist!"))
      return
    job = jobs[job_id]
    if len(indices) != len(job["tiers"]):
      await ctx.send(embed=ErrorEmbed("You must provide exactly one index for each tier!"))
      return
    new_tiers = []
    for i in indices:
      if i >= len(job["tiers"]):
        await ctx.send(embed=ErrorEmbed("That tier does not exist!"))
        return
      new_tiers.append(job["tiers"][i])
    job["tiers"] = new_tiers
    await self.config.JOBS.set(jobs)
    await ctx.send(embed=SettingChangedEmbed("Job Tiers Reordered", job["name"]))

  @command_econset_work_jobs.command(name="import", aliases=["load"])
  async def command_econset_work_jobs_import(self, ctx, *, data: str = None):
    """Import jobs from YAML in a code block. This will OVERWRITE all existing jobs!"""
    if len(ctx.message.attachments) == 1:
      if ctx.message.attachments[0].filename.endswith(".yaml") or ctx.message.attachments[0].filename.endswith(".yml"):
        data = await ctx.message.attachments[0].read()
    elif data:
      data = data.lstrip("```yaml").rstrip("```")
    else:
      await ctx.send(embed=ErrorEmbed("You must provide a YAML file or data!"))

    try:
      jobs = yaml.safe_load(data)
    except yaml.YAMLError as e:
      await ctx.send(embed=ErrorEmbed(title="YAML Error", message=str(e)))
      return

    await self.config.JOBS.set(jobs)

    await ctx.send(embed=SettingChangedEmbed("Jobs Imported", f"``py\n{pprint.pformat(jobs)[:256]}...\n``"))

  @command_econset_work_jobs.command(name="export", aliases=["dump", "save"])
  async def command_econset_work_jobs_export(self, ctx, to_file: bool = False):
    """Export jobs as YAML"""
    jobs = await self.config.JOBS()
    data = yaml.dump(jobs)
    if len(data) + 12 > 2000 or to_file:
      yaml_file = io.BytesIO(data.encode("utf-8"))
      await ctx.send(file=discord.File(yaml_file, filename=f"jobs_{ctx.guild.id}_{dt.datetime.now().strftime('%Y%m%d')}.yaml"))
    else:
      await ctx.send(f"```yaml\n{data}\n```")
