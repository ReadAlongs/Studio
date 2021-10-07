.. _advanced-use:

Data pre-processing and troubleshooting
=======================================

Pre-processing your data
------------------------

Manipulating the text and/or audio data that you are trying to align can
sometimes produce longer, more accurate ReadAlongs, that throw less
errors when aligning. While some of the most successful techniques we
have tried are outlined here, you may also need to customize your
pre-processing to suit your specific data.

Audio pre-processing
~~~~~~~~~~~~~~~~~~~~

Adding silences
^^^^^^^^^^^^^^^

Adding 1 second segments of silence in between phrases or paragraphs
sometimes improves the performance of the aligner. We do this using the
`Pydub <https://github.com/jiaaro/pydub>`__ library which can be
pip-installed. Keep in mind that Pydub uses milliseconds.

If your data is currently 1 audio file, you will need to split it into
segments where you want to put the silences.

::

   ten_seconds = 10 * 1000
   first_10_seconds = soundtrack[:ten_seconds]
   last_5_seconds = soundtrack[-5000:]

Once you have your segments, create an MP3 file containing only 1 second
of silence.

::

   from pydub import AudioSegment

   wfile = "appended_1000ms.mp3"
   silence = AudioSegment.silent(duration=1000)
   soundtrack = silence

Then you loop the audio files you want to append (segments and silence).

::

   seg = AudioSegment.from_mp3(mp3file)
   soundtrack = soundtrack + silence + seg

Write the soundtrack file as an MP3. This will then be the audio input
for your Read-Along.

::

   soundtrack.export(wfile, format="mp3")

Text pre-processing
~~~~~~~~~~~~~~~~~~~

Numbers
^^^^^^^

ReadAlong Studio cannot align numbers written as digits (ex. "123").
Instead, you will need to write them out (ex. "one two three" or "one
hundred and twenty three") depending on how they are read in your audio
file.

If you have lots of data, and the numbers are spoken in English (or any
of their supported languages), consider adding a library like
`num2words <https://github.com/savoirfairelinux/num2words>`__ to your
pre-processing.

::

   num2words 123456789
   one hundred and twenty-three million, four hundred and fifty-six thousand, seven hundred and eighty-nine

Troubleshooting
---------------

Here are three types of common errors you may encounter when trying to
run ReadAlongs, and ways to debug them. ### Phones missing in the
acoustic model You may get an error that looks like this:|image1| The
general structure of your error would look like
``Phone [character] is missing in the acoustic model; word [index] ignored``
This error is most likely caused not by a bug in your ReadAlong input
files, but by an error in one of your g2p mappings. The error message is
saying that there is a character in your ReadAlong text that is not
being properly converted to English-arpabet (eng-arpabet), which is the
language ReadAlong uses to map text to sound. Thus, ReadAlong cannot
match your text to a corresponding sound (phone) in your audio file
because it cannot understand what sound the text is meant to represent.
Follow these steps to debug the issue **in g2p**.

1. Identify which characters in each line of the error message are
   **not** being converted to eng-arpabet. These will either be:

   a. characters that are not in caps (for example ``g`` in the string
      ``gUW`` in the error message shown above.)
   b. a character not traditionally used in English (for example é or Ŧ,
      or ``ʰ`` in the error message shown above.) You can confirm you
      have isolated the right characters by ensuring every other
      character in your error message appears as an **output** in the
      `eng-ipa-to-arpabet
      mapping <https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json>`__.
      These are the problematic characters we need to debug in the error
      message shown above: ``g`` and ``ʰ``.

2. Once you have isolated the characters that are not being converted to
   eng-arpabet, you are ready to begin debugging the issue. Go through
   steps 3 - ? for each problematic character.

3. Our next step is to identify which mapping is converting the
   problematic characters incorrectly. Most of the time, the issue will
   be in either the first or the second of the following mappings:

   i.   *xyz-ipa* (where xyz is the ISO language code for your mapping)
   ii.  *xyz-equiv* (if you have one)
   iii. *xyz-ipa_to_eng-ipa* (this mapping must be generated
        automatically in g2p. Refer //here_in_the_guide to see how to do
        this.)
   iv.  `eng-ipa-to-arpabet
        mapping <https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json>`__
        (The issue is rarely found here, but it doesn’t hurt to check.)

4. Find a word in your text that uses the problematic character. For the
   sake of example, let us assume the character I am debugging is ``g``,
   that appears in the word "dog", in language "xyz".

5. Make sure you are in the g2p repository and run the word through
   ``g2p convert`` to confirm you have isolated the correct characters
   to debug: ``g2p convert dog xyz eng-arpabet``. Best practice is to
   copy+paste the word directly from your text instead of retyping it.
   Make sure to use the ISO code for your language in place of "xyz".
   *If the word converts cleanly into eng-arpabet characters, your issue
   does not lie in your mapping. //Refer to other potential RA issues*

6. From the result of the command run in 5, note the characters that do
   **not** appear as **inputs** in the `eng-ipa-to-arpabet
   mapping <https://github.com/roedoejet/g2p/blob/master/g2p/mappings/langs/eng/eng_ipa_to_arpabet.json>`__.
   These are the characters that have not been converted into characters
   that eng-ipa-to-arpabet can read. These should be the same characters
   you identified in step 2.

7. Run ``g2p convert dog xyz xyz-ipa``. Ensure the result is what you
   expect. If not, your error may arise from a problem in this mapping.
   refer_to_g2p_troubleshooting. If the result is what you expect,
   continue to the next step.

8. Note the result from running the command in 7. Check that the
   characters [TODO-fix this text] (appear/being mapped by generated --
   use debugger or just look at mapping)

.. |image1| image:: https://i.imgur.com/vKPhTud.png
